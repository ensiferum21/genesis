/*
 * mcx3: mcx2 (B20_R125) with a construct algebra over its program (B20_R153; `candidate_kinds/mcx3.py`).
 *
 * Why. Daniel, 27 Oct 2026: prioritise richer algorithm expressiveness, experimentally separated from improvements
 * in search, and let the languages improve on themselves (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`). mcx2's program is a
 * flat loop of physics operators with two guards; mcx3 adds generic CONTROL and ADDRESSING, once, so that programs
 * can say when and where an operator acts. It adds no search operator: the operators, and every function that
 * implements them, are mcx2's, unchanged (each line of mcx2.c from its includes to `relink` is here as it was).
 * The constructs are the builder's (human-designed infrastructure, labelled as such); the gain they carry, if any,
 * is a human LANGUAGE change and is never counted as Genesis's invention.
 *
 * The program is a list of ITEMS, run as the body of a loop until the CPU budget is spent:
 *   <op>[@<target>]  an mcx2 operator (B<k> b<k> X I C M H R D L, as in mcx2.c), optionally on chosen levels:
 *          @c the coldest level, @h the hottest, @a every level, @<digits> the levels named (0 = coldest, 0-7;
 *          levels the run does not have are ignored). Without a target each operator acts where it does in mcx2
 *          (B, X, I, D: every level; b, L, C: the coldest; M, H, R: the hottest); b takes no target (it is B@c).
 *          B and D act on both replicas of each level; X on the pairs (l, l+1) of each level l named; I within
 *          each level named; L, C, M, H and R on the first replica of each level named, coldest first
 *   S<k>   mcx2's stall guard: the next item runs only after k attractors (in all) without a new best; running it
 *          restarts the count
 *   P<k>   mcx2's period guard: the next item runs only on every k-th pass through the loop
 *   ?<o><c><v>  a guard over a run-time observable o compared (c: < or >) with an integer v; the next item runs
 *          only if it holds. Observables: f, the fraction of the budget spent (per mille); d, the diversity of the
 *          elite pool (the mean distance between two elites, a cut and its complement being the same cut, per
 *          mille of n; 0 with fewer than two elites); s, the spread of the replicas' cuts ((max - min) / |best|,
 *          per million); t, the attractors since the last new best (S's count, not restarted). Phases are guards
 *          on f
 *   *<k>   the next item runs k times (it is an operator, a block or a repeat, never a guard)
 *   [ ... ] a block: its items, in order, as one item, so that a guard or a repeat governs all of them
 * A guard that fails skips the next item, whatever it is (as in mcx2, a skipped guard is not evaluated, so the item
 * after it runs); a guard at the end of a block governs nothing. Items are separated by spaces or commas; brackets
 * are items of their own. A program has 1 to 512 items (blocks and repeats count), nesting at most 16 deep, and at
 * least one B or b. Named statements are expanded by the front end (`candidate_kinds/mcx3.py`, `expressive/`)
 * before a program reaches this interpreter.
 *
 * mcx2's programs are programs here and mean the same: on any mcx2 program, under the same seed and options, mcx3
 * makes the same random draws, the same clock readings and the same moves in the same order as mcx2, and returns
 * the same cut (a test builds both with a counting clock in place of the CPU clock and compares their outputs).
 * mcx3 accepts more than mcx2 (blocks, repeats, ?-guards, targets, more than 32 items).
 * Test builds only (`-DMCX3_PROBE`, never installed or pinned) report on stderr where each operator acts and each
 * observable with what it is computed from, so that the tests can recompute it.
 *
 * Input, output and options: as mcx2's (see mcx2.c), with mcx3's grammar for -prog. Exit 2: malformed input,
 * program or options; exit 3: a weighted degree too large for bucketed gains (> 2^24).
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <limits.h>

#define GAIN_LIMIT (1L << 24)
#define BLS_T 1000
#define BLS_Q 0.5

typedef struct {
    int n;
    int *off, *nbr; long *wt;
    long gmax;                  /* bound on |gain|: the largest weighted degree */
    int8_t *s; long *gain; long cut;
    int *bnext, *bprev, *bhead; long top;
    long *tabu, *moved; long iter;
} G;

static struct { double L0, P0; int tt_div, pool, restart, rs, pert; } prm = {0.01, 0.8, 10, 8, 2000, 0, 2};   /* BLS's */
static struct { int levels; double tmax, L0hot; } rex = {4, 0.5, 0.1};


static uint64_t rng_state;
static inline uint64_t rnd(void) { rng_state ^= rng_state << 13; rng_state ^= rng_state >> 7; rng_state ^= rng_state << 17; return rng_state; }
static inline double rnd01(void) { return (rnd() >> 11) * (1.0 / 9007199254740992.0); }

static double t_start, t_budget;
static double now(void) { return (double)clock() / CLOCKS_PER_SEC; }
static int out_of_time(void) { return now() - t_start >= t_budget; }

static void *xmalloc(size_t k) { void *p = malloc(k ? k : 1); if (!p) { fprintf(stderr, "out of memory\n"); exit(4); } return p; }
static void *xcalloc(size_t a, size_t b) { void *p = calloc(a ? a : 1, b); if (!p) { fprintf(stderr, "out of memory\n"); exit(4); } return p; }

static G *g_new(int n, int *off, int *nbr, long *wt) {
    G *g = xcalloc(1, sizeof(G));
    g->n = n; g->off = off; g->nbr = nbr; g->wt = wt; g->gmax = 1;
    for (int v = 0; v < n; v++) {
        long a = 0;
        for (int k = off[v]; k < off[v + 1]; k++) a += labs(wt[k]);
        if (a > g->gmax) g->gmax = a;
    }
    if (g->gmax > GAIN_LIMIT) return g;          /* the caller refuses it */
    g->s = xcalloc(n, 1); g->gain = xmalloc(sizeof(long) * n);
    g->bnext = xmalloc(sizeof(int) * n); g->bprev = xmalloc(sizeof(int) * n);
    g->bhead = xmalloc(sizeof(int) * (2 * g->gmax + 1));
    g->tabu = xcalloc(n, sizeof(long)); g->moved = xcalloc(n, sizeof(long));
    return g;
}

static void g_free(G *g) {
    free(g->off); free(g->nbr); free(g->wt); free(g->s); free(g->gain); free(g->bnext); free(g->bprev);
    free(g->bhead); free(g->tabu); free(g->moved); free(g);
}

static void bucket_insert(G *g, int v) {
    long b = g->gain[v] + g->gmax;
    g->bprev[v] = -1; g->bnext[v] = g->bhead[b];
    if (g->bhead[b] >= 0) g->bprev[g->bhead[b]] = v;
    g->bhead[b] = v;
    if (b > g->top) g->top = b;
}
static void bucket_remove(G *g, int v) {
    long b = g->gain[v] + g->gmax;
    if (g->bprev[v] >= 0) g->bnext[g->bprev[v]] = g->bnext[v]; else g->bhead[b] = g->bnext[v];
    if (g->bnext[v] >= 0) g->bprev[g->bnext[v]] = g->bprev[v];
}
static void fix_top(G *g) { while (g->top > 0 && g->bhead[g->top] < 0) g->top--; }

static void compute_all(G *g) {
    g->cut = 0;
    for (long b = 0; b <= 2 * g->gmax; b++) g->bhead[b] = -1;
    g->top = 0;
    for (int v = 0; v < g->n; v++) {
        long x = 0;
        for (int k = g->off[v]; k < g->off[v + 1]; k++) {
            int u = g->nbr[k];
            if (g->s[u] == g->s[v]) x += g->wt[k]; else { x -= g->wt[k]; if (u > v) g->cut += g->wt[k]; }
        }
        g->gain[v] = x;
        bucket_insert(g, v);
    }
    fix_top(g);
}

static void flip(G *g, int v) {
    g->cut += g->gain[v];
    bucket_remove(g, v);
    for (int k = g->off[v]; k < g->off[v + 1]; k++) {
        int u = g->nbr[k];
        bucket_remove(g, u);
        /* before the flip: same side -> the edge becomes cut (u's gain drops by 2w); opposite -> rises by 2w */
        if (g->s[u] == g->s[v]) g->gain[u] -= 2L * g->wt[k]; else g->gain[u] += 2L * g->wt[k];
        bucket_insert(g, u);
    }
    g->s[v] ^= 1;
    g->gain[v] = -g->gain[v];
    bucket_insert(g, v);
    fix_top(g);
}

static void make_tabu(G *g, int v) {
    g->tabu[v] = g->iter + 3 + (long)(rnd() % (unsigned long)(g->n / prm.tt_div + 1));
}

/* steepest ascent: flip the best vertex while it improves (with -pert 2 the moves are also made tabu, as in BLS) */
static void ascend(G *g) {
    int steps = 0;
    while (g->top > g->gmax) {
        int v = g->bhead[g->top];
        flip(g, v);
        if (prm.pert == 2) { g->iter++; g->moved[v] = g->iter; make_tabu(g, v); }
        if ((++steps & 1023) == 0 && out_of_time()) return;
    }
}

/* best non-tabu vertex (aspiration: a tabu move that gives a new best cut is allowed) */
static int best_nontabu(G *g, long best_cut) {
    for (long b = g->top; b >= 0; b--)
        for (int v = g->bhead[b]; v >= 0; v = g->bnext[v])
            if (g->tabu[v] <= g->iter || g->cut + g->gain[v] > best_cut) return v;
    return (int)(rnd() % g->n);
}

/* the same on one side only (BLS's M2); -1 if every vertex of that side is tabu */
static int best_nontabu_side(G *g, long best_cut, int side) {
    for (long b = g->top; b >= 0; b--)
        for (int v = g->bhead[b]; v >= 0; v = g->bnext[v])
            if (g->s[v] == side && (g->tabu[v] <= g->iter || g->cut + g->gain[v] > best_cut)) return v;
    return -1;
}

/* the elite pool (fine level) */
static int8_t **elite;
static long *elite_cut;
static int elites;

static void pool_offer(G *g) {
    for (int i = 0; i < elites; i++) if (elite_cut[i] == g->cut && memcmp(elite[i], g->s, g->n) == 0) return;
    int worst;
    if (elites < prm.pool) worst = elites++;
    else {
        worst = 0;
        for (int i = 1; i < elites; i++) if (elite_cut[i] < elite_cut[worst]) worst = i;
        if (elite_cut[worst] >= g->cut) return;
    }
    memcpy(elite[worst], g->s, g->n); elite_cut[worst] = g->cut;
}

typedef struct { long L, Lmin, Lmax, since, last_cut, omega; int strong; int8_t *last_opt; } Walk;

static void walk_init(Walk *w, G *g) {
    w->Lmin = (long)(prm.L0 * g->n); if (w->Lmin < 1) w->Lmin = 1;
    w->Lmax = g->n / 10 > w->Lmin ? g->n / 10 : w->Lmin + 1;
    w->L = w->Lmin; w->since = 0; w->last_cut = g->cut; w->omega = 0; w->strong = 0;
    w->last_opt = xmalloc(g->n); memcpy(w->last_opt, g->s, g->n);
}

static void perturb(G *g, Walk *w, int8_t *best, long *best_cut) {
    int mode, n = g->n;             /* 0 directed flips, 1 recency-based, 2 random, 3 directed pairs (BLS's M2) */
    if (prm.pert == 2) {
        if (w->strong) { mode = 2; w->strong = 0; }
        else {
            double P = exp(-(double)w->omega / BLS_T), r = rnd01();
            if (P < prm.P0) P = prm.P0;
            mode = r < P * BLS_Q ? 0 : (r < P ? 3 : 2);
        }
    } else {
        double P = w->since > 1000 ? prm.P0 : 1.0 - (1.0 - prm.P0) * w->since / 1000.0;
        mode = rnd01() < P ? 0 : (prm.pert == 1 && rnd01() < 0.5 ? 1 : 2);
    }
    for (long k = 0; k < w->L; k++) {
        int v;
        if (mode == 3) {
            int a = best_nontabu_side(g, *best_cut, 0), b = best_nontabu_side(g, *best_cut, 1);
            for (int j = 0; j < 2; j++) {
                int x = j ? b : a;
                if (x < 0) continue;
                flip(g, x); g->iter++; g->moved[x] = g->iter; make_tabu(g, x);
                if (g->cut > *best_cut) { *best_cut = g->cut; memcpy(best, g->s, n); }
            }
            continue;
        }
        if (mode == 0) v = best_nontabu(g, *best_cut);
        else if (mode == 1) {
            v = (int)(rnd() % n);
            for (int j = 1; j < 8; j++) { int x = (int)(rnd() % n); if (g->moved[x] < g->moved[v]) v = x; }
        } else v = (int)(rnd() % n);
        flip(g, v);
        g->iter++;
        g->moved[v] = g->iter;
        if (mode == 0 || prm.pert == 2) make_tabu(g, v);
        if (g->cut > *best_cut) { *best_cut = g->cut; memcpy(best, g->s, n); }
    }
}

/* iterated tabu search from the current state; returns 1 when `limit` attractors without a new best have passed
   (since the last such return), 0 when the time is spent */
static int its(G *g, Walk *w, int8_t *best, long *best_cut, long limit, int fine) {
    while (!out_of_time()) {
        long before = *best_cut;
        perturb(g, w, best, best_cut);
        ascend(g);
        if (g->cut > *best_cut) { *best_cut = g->cut; memcpy(best, g->s, g->n); }
        if (*best_cut > before) w->since = w->omega = 0;
        else { w->since++; if (++w->omega > BLS_T && prm.pert == 2) { w->omega = 0; w->strong = 1; } }
        if (g->cut == w->last_cut && memcmp(g->s, w->last_opt, g->n) == 0) { if (++w->L > w->Lmax) w->L = w->Lmax; }
        else { w->L = w->Lmin; w->last_cut = g->cut; memcpy(w->last_opt, g->s, g->n); }
        if (fine) pool_offer(g);
        if (w->since > 0 && w->since % limit == 0) return 1;
    }
    return 0;
}

/* Houdayer-style cluster exchange into g->s: start from elite a; each cluster of disagreement with b is taken from b
   with probability 1/2 */
static int *stackv, *mark;
static void cluster_exchange(G *g, int a, int b) {
    int n = g->n;
    memcpy(g->s, elite[a], n);
    for (int v = 0; v < n; v++) mark[v] = 0;
    for (int v = 0; v < n; v++) {
        if (mark[v] || elite[a][v] == elite[b][v]) continue;
        int take = rnd() & 1, sp = 0;
        stackv[sp++] = v; mark[v] = 1;
        while (sp) {
            int x = stackv[--sp];
            if (take) g->s[x] = elite[b][x];
            for (int k = g->off[x]; k < g->off[x + 1]; k++) {
                int y = g->nbr[k];
                if (!mark[y] && elite[a][y] != elite[b][y]) { mark[y] = 1; stackv[sp++] = y; }
            }
        }
    }
}

/* MACUT's multi-parent grouping crossover into g->s */
static void macut_crossover(G *g) {
    int idx[1024], m = 2 + (int)(rnd() % 3);
    if (m > elites) m = elites;
    for (int i = 0; i < elites; i++) idx[i] = i;
    for (int i = 0; i < m; i++) { int j = i + (int)(rnd() % (unsigned long)(elites - i)); int x = idx[i]; idx[i] = idx[j]; idx[j] = x; }
    long cnt[16] = {0};
    for (int v = 0; v < g->n; v++) {
        int p = 0;
        for (int i = 0; i < m; i++) p |= elite[idx[i]][v] << i;
        mark[v] = p;
        cnt[p]++;
    }
    int first = 0, second = -1;
    for (int p = 1; p < (1 << m); p++) if (cnt[p] > cnt[first]) first = p;
    for (int p = 0; p < (1 << m); p++) if (p != first && (second < 0 || cnt[p] > cnt[second])) second = p;
    for (int v = 0; v < g->n; v++) g->s[v] = mark[v] == first ? 0 : mark[v] == second ? 1 : (int8_t)(rnd() & 1);
}

/* renormalisation: union-find with parity over the edges all elites orient alike */
static int *uf_p, *uf_sz, *cid, *cof;
static int8_t *uf_x, *cpar;
typedef struct { int a, b; long w; } Tri;
static Tri *tri;

static int uf_find(int v, int8_t *px) {
    int r = v; int8_t acc = 0;
    while (uf_p[r] != r) { acc ^= uf_x[r]; r = uf_p[r]; }
    *px = acc;
    while (uf_p[v] != r && v != r) {              /* path compression, keeping parities relative to the root */
        int next = uf_p[v]; int8_t xv = uf_x[v];
        uf_p[v] = r; uf_x[v] = acc;
        acc ^= xv; v = next;
    }
    return r;
}

static void uf_unite(int u, int v, int8_t rel) {     /* s_u xor s_v = rel */
    int8_t pu, pv;
    int ru = uf_find(u, &pu), rv = uf_find(v, &pv);
    if (ru == rv) return;
    if (uf_sz[ru] < uf_sz[rv]) { int t = ru; ru = rv; rv = t; }
    uf_p[rv] = ru; uf_x[rv] = rel ^ pu ^ pv; uf_sz[ru] += uf_sz[rv];
}

static int tri_cmp(const void *x, const void *y) {
    const Tri *a = x, *b = y;
    if (a->a != b->a) return a->a < b->a ? -1 : 1;
    if (a->b != b->b) return a->b < b->b ? -1 : 1;
    return 0;
}

/* 1 if a coarse step was made (g->s then holds the projected, polished state), 0 if nothing contracts usefully */
static int coarse_step(G *g) {
    int n = g->n;
    for (int v = 0; v < n; v++) { uf_p[v] = v; uf_x[v] = 0; uf_sz[v] = 1; cid[v] = -1; }
    for (int v = 0; v < n; v++)
        for (int k = g->off[v]; k < g->off[v + 1]; k++) {
            int u = g->nbr[k];
            if (u <= v) continue;
            int8_t r0 = elite[0][v] ^ elite[0][u];
            int agree = 1;
            for (int i = 1; i < elites && agree; i++) if ((elite[i][v] ^ elite[i][u]) != r0) agree = 0;
            if (agree) uf_unite(v, u, r0);
        }
    int nc = 0;
    for (int v = 0; v < n; v++) {
        int r = uf_find(v, &cpar[v]);
        if (cid[r] < 0) cid[r] = nc++;
        cof[v] = cid[r];
    }
    if (nc < 2 || nc == n) return 0;
    long mt = 0;
    for (int v = 0; v < n; v++)
        for (int k = g->off[v]; k < g->off[v + 1]; k++) {
            int u = g->nbr[k];
            if (u <= v || cof[u] == cof[v]) continue;
            int a = cof[v], b = cof[u];
            tri[mt].a = a < b ? a : b; tri[mt].b = a < b ? b : a;
            tri[mt++].w = cpar[v] == cpar[u] ? g->wt[k] : -g->wt[k];
        }
    qsort(tri, mt, sizeof(Tri), tri_cmp);
    long mc = 0;
    for (long i = 0; i < mt; i++) {
        if (mc > 0 && tri[mc - 1].a == tri[i].a && tri[mc - 1].b == tri[i].b) tri[mc - 1].w += tri[i].w;
        else tri[mc++] = tri[i];
    }
    long k2 = 0;
    for (long i = 0; i < mc; i++) if (tri[i].w != 0) tri[k2++] = tri[i];
    mc = k2;
    if (mc == 0) return 0;
    int *off = xcalloc(nc + 1, sizeof(int)), *nbr = xmalloc(sizeof(int) * 2 * mc);
    long *wt = xmalloc(sizeof(long) * 2 * mc);
    for (long i = 0; i < mc; i++) { off[tri[i].a + 1]++; off[tri[i].b + 1]++; }
    for (int c = 0; c < nc; c++) off[c + 1] += off[c];
    int *fill = xcalloc(nc, sizeof(int));
    for (long i = 0; i < mc; i++) {
        int a = tri[i].a, b = tri[i].b;
        nbr[off[a] + fill[a]] = b; wt[off[a] + fill[a]++] = tri[i].w;
        nbr[off[b] + fill[b]] = a; wt[off[b] + fill[b]++] = tri[i].w;
    }
    free(fill);
    G *c = g_new(nc, off, nbr, wt);
    if (c->gmax > GAIN_LIMIT) { free(off); free(nbr); free(wt); free(c); return 0; }
    int eb = 0;
    for (int i = 1; i < elites; i++) if (elite_cut[i] > elite_cut[eb]) eb = i;
    for (int v = 0; v < n; v++) c->s[cof[v]] = elite[eb][v] ^ cpar[v];
    compute_all(c);
    ascend(c);
    int8_t *cbest = xmalloc(nc); memcpy(cbest, c->s, nc);
    long cbc = c->cut;
    Walk cw; walk_init(&cw, c);
    its(c, &cw, cbest, &cbc, prm.restart, 0);
    for (int v = 0; v < n; v++) g->s[v] = cbest[cof[v]] ^ cpar[v];
    free(cbest); free(cw.last_opt); g_free(c);
    compute_all(g);
    ascend(g);
    return 1;
}

/* ------------------------------------------------------------------ replicas (B20_R125) */
typedef struct { G *g; Walk w; } Rep;

/* set a walk's perturbation strength for a level (keeps its memory of the last local optimum) */
static void walk_level(Walk *w, G *g, double L0) {
    w->Lmin = (long)(L0 * g->n); if (w->Lmin < 1) w->Lmin = 1;
    w->Lmax = g->n / 10 > w->Lmin ? g->n / 10 : w->Lmin + 1;
    w->L = w->Lmin;
}

/* an isoenergetic cluster move between two replicas; 1 if one was made */
static int icm_move(G *a, G *b) {
    int n = a->n, diff = 0;
    for (int v = 0; v < n; v++) diff += a->s[v] != b->s[v];
    if (diff > n / 2) {                           /* align: the complement of a cut is the same cut, gains unchanged */
        for (int v = 0; v < n; v++) b->s[v] ^= 1;
        diff = n - diff;
    }
    if (diff == 0) return 0;
    int start = (int)(rnd() % (unsigned long)n), v0 = -1;
    for (int i = 0; i < n; i++) { int v = (start + i) % n; if (a->s[v] != b->s[v]) { v0 = v; break; } }
    for (int v = 0; v < n; v++) mark[v] = 0;
    int sp = 0, size = 0;
    stackv[sp++] = v0; mark[v0] = 1;
    while (sp) {                                  /* the cluster: connected disagreeing vertices, collected first */
        int x = stackv[--sp];
        mark[x] = 2; size++;
        for (int k = a->off[x]; k < a->off[x + 1]; k++) {
            int y = a->nbr[k];
            if (!mark[y] && a->s[y] != b->s[y]) { mark[y] = 1; stackv[sp++] = y; }
        }
    }
    if (size > n / 2) return 0;
    for (int v = 0; v < n; v++) if (mark[v] == 2) { flip(a, v); flip(b, v); }
    return 1;
}

/* MOH's double-transfer move: 1 if a pair was flipped */
static int pair_descent(G *g) {
    int moved = 0;
    for (int round = 0; round < 1000 && !out_of_time(); round++) {
        long bestg = 0; int bu = -1, bv = -1;
        for (int u = 0; u < g->n; u++)
            for (int k = g->off[u]; k < g->off[u + 1]; k++) {
                int v = g->nbr[k];
                if (v <= u) continue;
                long pg = g->gain[u] + g->gain[v] - 2L * g->wt[k] * (g->s[u] == g->s[v] ? 1 : -1);
                if (pg > bestg) { bestg = pg; bu = u; bv = v; }
            }
        if (bu < 0) break;
        flip(g, bu); flip(g, bv); moved = 1;
        ascend(g);
    }
    return moved;
}

/* path relinking from g's state towards elite e (aligned: a cut and its complement are the same cut); 1 if done */
static int relink(G *g, int e) {
    int n = g->n, diff = 0;
    int8_t *t = elite[e];
    for (int v = 0; v < n; v++) diff += g->s[v] != t[v];
    int8_t comp = diff > n / 2;
    int cnt = 0;
    for (int v = 0; v < n; v++) if ((int8_t)(g->s[v] ^ comp) != t[v]) stackv[cnt++] = v;
    if (cnt < 2) return 0;
    long best = g->cut; int bestk = -1, last = -1;
    for (int step = 0; step < cnt - 1; step++) {
        int bi = step; long bg = g->gain[stackv[step]];
        for (int i = step + 1; i < cnt; i++) if (g->gain[stackv[i]] > bg) { bg = g->gain[stackv[i]]; bi = i; }
        int x = stackv[step]; stackv[step] = stackv[bi]; stackv[bi] = x;
        flip(g, stackv[step]);
        last = step;
        if (g->cut > best) { best = g->cut; bestk = step; }
        if ((step & 255) == 0 && out_of_time()) break;
    }
    for (int i = last; i > bestk; i--) flip(g, stackv[i]);      /* back to the best state on the path */
    ascend(g);
    return 1;
}

/* ------------------------------------------------------------------ the program (B20_R153) */
enum { K_OP, K_GUARD, K_REPEAT, K_BLOCK };
enum { T_DEF, T_COLD, T_HOT, T_ALL, T_SET };
typedef struct { char kind, op, obs, cmp, tgt; unsigned set; long arg; int child, next; } Node;
#define MAXNODE 512
#define MAXDEPTH 16
#define MAXTOK 1024
static Node node[MAXNODE];
static int nnode, first_item, has_b;
static char toks[MAXTOK][32];
static int ntok, tp;
static const char *DEFAULT_PROG = "B100 X I S2000 C";

/* the run's state, which every item reads and writes (in mcx2, locals of main) */
static Rep *rp;
static int *slot, nv, NL, NR;                       /* slot[2 l + k]: the replica at level l, place k */
static double *Tl, *L0l;                            /* level temperatures and perturbation strengths */
static int8_t *best;
static long best_cut, since, pass;                  /* attractors in all since the last new best; loop passes */
#define NOTE(h) do { pool_offer(h); if ((h)->cut > best_cut) { best_cut = (h)->cut; memcpy(best, (h)->s, nv); since = 0; } } while (0)

static int tokenize(const char *s) {
    ntok = 0;
    while (*s) {
        while (*s == ' ' || *s == ',') s++;
        if (!*s) break;
        if (ntok >= MAXTOK) return 0;
        int k = 0;
        while (*s && *s != ' ' && *s != ',') { if (k >= 31) return 0; toks[ntok][k++] = *s++; }
        toks[ntok++][k] = 0;
    }
    return 1;
}

/* the digits at *p into *v: their count, 0 if none, -1 if more than 9 */
static int digits(const char **p, long *v) {
    int d = 0; *v = 0;
    while (**p >= '0' && **p <= '9') { *v = *v * 10 + (*(*p)++ - '0'); if (++d > 9) return -1; }
    return d;
}

static int new_node(char kind) {
    if (nnode >= MAXNODE) return -1;
    Node *x = &node[nnode];
    memset(x, 0, sizeof *x);
    x->kind = kind; x->child = x->next = -1;
    return nnode++;
}

static int parse_list(int depth);

/* one item from the token stream: its node, -1 if malformed */
static int parse_item(int depth) {
    const char *t = toks[tp++], *p = t + 1;
    char c = t[0];
    long v; int i, d;
    if (!strcmp(t, "[")) {
        if (depth + 1 > MAXDEPTH || (i = new_node(K_BLOCK)) < 0) return -1;
        int f = parse_list(depth + 1);
        if (f < 0) return -1;                                   /* malformed, or an empty block */
        node[i].child = f;
        return i;
    }
    if (c == '*') {
        if (digits(&p, &v) <= 0 || *p || v < 1 || tp >= ntok || depth + 1 > MAXDEPTH) return -1;
        char e = toks[tp][0];
        if (!strcmp(toks[tp], "]") || e == 'S' || e == 'P' || e == '?') return -1;   /* never a guard */
        if ((i = new_node(K_REPEAT)) < 0) return -1;
        node[i].arg = v;
        int ch = parse_item(depth + 1);
        if (ch < 0) return -1;
        node[i].child = ch;
        return i;
    }
    if (c == 'S' || c == 'P') {
        if (digits(&p, &v) <= 0 || *p || v < 1 || (i = new_node(K_GUARD)) < 0) return -1;
        node[i].op = c; node[i].arg = v;
        return i;
    }
    if (c == '?') {
        char o = t[1];
        if (!o || !strchr("fdst", o) || (t[2] != '<' && t[2] != '>')) return -1;
        p = t + 3;
        if (digits(&p, &v) <= 0 || *p || (i = new_node(K_GUARD)) < 0) return -1;
        node[i].op = '?'; node[i].obs = o; node[i].cmp = t[2]; node[i].arg = v;
        return i;
    }
    if (!c || !strchr("BbXICMHRDL", c)) return -1;
    int needs = c == 'B' || c == 'b';
    d = digits(&p, &v);
    if (d < 0 || needs != (d > 0) || (needs && v < 1)) return -1;
    int tg = T_DEF; unsigned set = 0;
    if (*p == '@') {
        p++;
        if (c == 'b') return -1;                                /* b is B@c */
        if (*p == 'c' || *p == 'h' || *p == 'a') { tg = *p == 'c' ? T_COLD : *p == 'h' ? T_HOT : T_ALL; p++; }
        else {
            tg = T_SET;
            while (*p >= '0' && *p <= '7') set |= 1u << (*p++ - '0');
            if (!set) return -1;
        }
    }
    if (*p || (i = new_node(K_OP)) < 0) return -1;
    node[i].op = c; node[i].arg = needs ? v : 0; node[i].tgt = (char)tg; node[i].set = set;
    if (needs) has_b = 1;
    return i;
}

/* the items up to "]" (depth > 0) or to the end (depth 0): the first item's node, -1 if there is none, -2 if
   malformed */
static int parse_list(int depth) {
    int first = -1, last = -1;
    while (tp < ntok && strcmp(toks[tp], "]")) {
        int i = parse_item(depth);
        if (i < 0) return -2;
        if (last < 0) first = i; else node[last].next = i;
        last = i;
    }
    if (depth > 0) { if (tp >= ntok) return -2; tp++; }        /* the closing bracket */
    else if (tp < ntok) return -2;                             /* a "]" with no "[" */
    return first;
}

static int parse_prog(const char *s) {
    nnode = 0; has_b = 0; tp = 0;
    if (!tokenize(s)) return 0;
    first_item = parse_list(0);
    return first_item >= 0 && has_b;
}

/* the levels an operator acts on, coldest first; def: where it acts without a target */
static int levels_of(const Node *x, int def, int *lv) {
    int t = x->tgt == T_DEF ? def : x->tgt, k = 0;
    for (int l = 0; l < NL; l++)
        if (t == T_ALL || (t == T_COLD && l == 0) || (t == T_HOT && l == NL - 1) || (t == T_SET && (x->set >> l & 1)))
            lv[k++] = l;
    return k;
}

/* one operator; with its default target it does exactly what the same statement does in mcx2 */
#ifdef MCX3_PROBE                                   /* test builds only: report where each operator acts */
static void probe_op(const Node *x, int def) {
    int lv[8], nl = levels_of(x, def, lv);
    fprintf(stderr, "op %c", x->op);
    for (int i = 0; i < nl; i++) fprintf(stderr, " %d", lv[i]);
    fprintf(stderr, "\n");
}
#endif

static void exec_op(const Node *x) {
    int lv[8], pos[16], nl, np = 0;
    char op = x->op;
#ifdef MCX3_PROBE
    probe_op(x, (op == 'b' || op == 'L' || op == 'C') ? T_COLD : strchr("MHR", op) ? T_HOT : T_ALL);
#endif
    if (op == 'B' || op == 'b' || op == 'D') {
        nl = levels_of(x, op == 'b' ? T_COLD : T_ALL, lv);
        for (int i = 0; i < nl; i++) { pos[np++] = 2 * lv[i]; pos[np++] = 2 * lv[i] + 1; }
    }
    if (op == 'B' || op == 'b') {
        for (int q = 0; q < np && !out_of_time(); q++) {
            Rep *r = &rp[slot[pos[q]]];
            for (long i = 0; i < x->arg && !out_of_time(); i++) {
                long rb = best_cut;
                perturb(r->g, &r->w, best, &rb);
                ascend(r->g);
                Walk *w = &r->w; G *h = r->g;
                if (h->cut == w->last_cut && memcmp(h->s, w->last_opt, nv) == 0) { if (++w->L > w->Lmax) w->L = w->Lmax; }
                else { w->L = w->Lmin; w->last_cut = h->cut; memcpy(w->last_opt, h->s, nv); }
                if (rb > best_cut) {                     /* a new best was seen during the perturbation */
                    best_cut = rb; if (h->cut == rb) memcpy(best, h->s, nv); since = 0; w->omega = 0;
                } else if (h->cut > best_cut) { best_cut = h->cut; memcpy(best, h->s, nv); since = 0; w->omega = 0; }
                else { since++; if (++w->omega > BLS_T && prm.pert == 2) { w->omega = 0; w->strong = 1; } }
                pool_offer(h);
            }
        }
    } else if (op == 'X') {
        nl = levels_of(x, T_ALL, lv);
        for (int i = 0; i < nl; i++) {
            int l = lv[i];
            if (l + 1 >= NL) continue;
            for (int k = 0; k < 2; k++) {
                int a = slot[2 * l + k], b = slot[2 * (l + 1) + k];
                double d = (1.0 / Tl[l] - 1.0 / Tl[l + 1]) * (double)(rp[b].g->cut - rp[a].g->cut);
                if (d >= 0 || rnd01() < exp(d)) {
                    slot[2 * l + k] = b; slot[2 * (l + 1) + k] = a;
                    walk_level(&rp[b].w, rp[b].g, L0l[l]); walk_level(&rp[a].w, rp[a].g, L0l[l + 1]);
                }
            }
        }
    } else if (op == 'I') {
        nl = levels_of(x, T_ALL, lv);
        for (int i = 0; i < nl && !out_of_time(); i++) {
            int l = lv[i];
            G *ga = rp[slot[2 * l]].g, *gb = rp[slot[2 * l + 1]].g;
            if (icm_move(ga, gb)) { ascend(ga); ascend(gb); NOTE(ga); NOTE(gb); }
        }
    } else if (op == 'D') {
        for (int q = 0; q < np && !out_of_time(); q++) { G *h = rp[slot[pos[q]]].g; if (pair_descent(h)) NOTE(h); }
    } else if (op == 'L') {
        nl = levels_of(x, T_COLD, lv);
        for (int i = 0; i < nl; i++) {
            if (i > 0 && out_of_time()) break;
            G *h = rp[slot[2 * lv[i]]].g;
            if (elites >= 1 && relink(h, (int)(rnd() % elites))) NOTE(h);
        }
    } else if (op == 'C') {
        nl = levels_of(x, T_COLD, lv);
        for (int i = 0; i < nl; i++) {
            if (i > 0 && out_of_time()) break;
            int l = lv[i];
            G *h = rp[slot[2 * l]].g;
            if (elites >= 2 && coarse_step(h)) { NOTE(h); walk_level(&rp[slot[2 * l]].w, h, L0l[l]); }
        }
    } else {                                     /* M, H, R: by default on the hottest replica */
        nl = levels_of(x, T_HOT, lv);
        for (int i = 0; i < nl; i++) {
            if (i > 0 && out_of_time()) break;
            int l = lv[i], q = slot[2 * l];
            G *h = rp[q].g;
            if (op == 'R') for (int v = 0; v < nv; v++) h->s[v] = rnd() & 1;
            else if (elites < 2) continue;
            else if (op == 'M') macut_crossover(h);
            else { int a = (int)(rnd() % elites), b = (int)(rnd() % (elites - 1)); if (b >= a) b++; cluster_exchange(h, a, b); }
            compute_all(h); ascend(h); NOTE(h);
            walk_level(&rp[q].w, h, L0l[l]);
        }
    }
}

/* a run-time observable (see the header) */
static long observe(char o) {
    if (o == 'f') return (long)((now() - t_start) / t_budget * 1000.0);
    if (o == 't') return since;
    if (o == 's') {
        long lo = LONG_MAX, hi = LONG_MIN, b = labs(best_cut);
        for (int r = 0; r < NR; r++) { long c = rp[r].g->cut; if (c < lo) lo = c; if (c > hi) hi = c; }
        return (long)((double)(hi - lo) * 1e6 / (double)(b < 1 ? 1 : b));
    }
    if (elites < 2) return 0;                    /* 'd' */
    double sum = 0; long pairs = 0;
    for (int i = 0; i < elites; i++)
        for (int j = i + 1; j < elites; j++) {
            long h = 0;
            for (int v = 0; v < nv; v++) h += elite[i][v] != elite[j][v];
            sum += h > nv - h ? nv - h : h; pairs++;
        }
    return (long)(sum / pairs / nv * 1000.0);
}

static int holds(const Node *x) {
    if (x->op == 'S') { if (since >= x->arg) { since = 0; return 1; } return 0; }
    if (x->op == 'P') return pass % x->arg == 0;
    long v = observe(x->obs);
#ifdef MCX3_PROBE                                   /* test builds only: the observable and what it is made of */
    fprintf(stderr, "obs %c %ld", x->obs, v);
    if (x->obs == 'd') { fprintf(stderr, " %d", elites); for (int i = 0; i < elites; i++) { fputc(' ', stderr); for (int u = 0; u < nv; u++) fputc('0' + elite[i][u], stderr); } }
    if (x->obs == 's') { fprintf(stderr, " %ld", best_cut); for (int r = 0; r < NR; r++) fprintf(stderr, " %ld", rp[r].g->cut); }
    if (x->obs == 't') fprintf(stderr, " %ld", pass);
    fprintf(stderr, "\n");
#endif
    return x->cmp == '<' ? v < x->arg : v > x->arg;
}

static void run_list(int i);

static void run_item(int i) {
    const Node *x = &node[i];
    if (x->kind == K_OP) exec_op(x);
    else if (x->kind == K_BLOCK) run_list(x->child);
    else for (long r = 0; r < x->arg && !out_of_time(); r++) run_item(x->child);     /* a repeat */
}

/* a list of items, in order, while time is left; a guard that fails skips the next item (mcx2's rule) */
static void run_list(int i) {
    int skip = 0;
    for (; i >= 0 && !out_of_time(); i = node[i].next) {
        if (skip) { skip = 0; continue; }
        if (node[i].kind == K_GUARD) { skip = !holds(&node[i]); continue; }
        run_item(i);
    }
}

static int opt(const char *name, const char *val) {
    if (!strcmp(name, "-prog")) return parse_prog(val);
    char *end;
    double x = strtod(val, &end);
    if (*end) return 0;
    if (!strcmp(name, "-L0") && x > 0 && x <= 1) prm.L0 = x;
    else if (!strcmp(name, "-P") && x >= 0 && x <= 1) prm.P0 = x;
    else if (!strcmp(name, "-tt") && x >= 1 && x <= 1e6 && x == (int)x) prm.tt_div = (int)x;
    else if (!strcmp(name, "-pool") && x >= 2 && x <= 1024 && x == (int)x) prm.pool = (int)x;
    else if (!strcmp(name, "-restart") && x >= 1 && x <= 1e9 && x == (int)x) prm.restart = (int)x;
    else if (!strcmp(name, "-rs") && (x == 0 || x == 1 || x == 2 || x == 3)) prm.rs = (int)x;
    else if (!strcmp(name, "-pert") && (x == 0 || x == 1 || x == 2)) prm.pert = (int)x;
    else if (!strcmp(name, "-levels") && x >= 1 && x <= 8 && x == (int)x) rex.levels = (int)x;
    else if (!strcmp(name, "-tmax") && x > 0 && x <= 100) rex.tmax = x;
    else if (!strcmp(name, "-L0hot") && x > 0 && x <= 1) rex.L0hot = x;
    else return 0;
    return 1;
}

int main(int argc, char **argv) {
    if (argc % 2 != 1) { fprintf(stderr, "options come in pairs\n"); return 2; }
    for (int i = 1; i + 1 < argc; i += 2)
        if (!opt(argv[i], argv[i + 1])) { fprintf(stderr, "bad option %s %s\n", argv[i], argv[i + 1]); return 2; }
    int given = 0;
    for (int i = 1; i + 1 < argc; i += 2) if (!strcmp(argv[i], "-prog")) given = 1;
    if (!given) parse_prog(DEFAULT_PROG);
    t_start = now();
    int n, m;
    unsigned long long seed; double budget_ms;
    if (scanf("%d %d %llu %lf", &n, &m, &seed, &budget_ms) != 4 || n < 1 || m < 0 || !(budget_ms > 0)) {
        fprintf(stderr, "bad header\n"); return 2; }
    t_budget = budget_ms / 1000.0;
    rng_state = seed * 0x9E3779B97F4A7C15ULL + 1;
    int *eu = xmalloc(sizeof(int) * m), *ev = xmalloc(sizeof(int) * m);
    long *ew = xmalloc(sizeof(long) * m);
    int *deg = xcalloc(n, sizeof(int));
    for (int i = 0; i < m; i++) {
        if (scanf("%d %d %ld", &eu[i], &ev[i], &ew[i]) != 3 || eu[i] < 0 || ev[i] < 0 || eu[i] >= n || ev[i] >= n
            || eu[i] == ev[i] || ew[i] == 0) { fprintf(stderr, "bad edge\n"); return 2; }
        deg[eu[i]]++; deg[ev[i]]++;
    }
    int *off = xmalloc(sizeof(int) * (n + 1)); off[0] = 0;
    for (int v = 0; v < n; v++) off[v + 1] = off[v] + deg[v];
    int *nbr = xmalloc(sizeof(int) * 2 * (size_t)m); long *wt = xmalloc(sizeof(long) * 2 * (size_t)m);
    int *fill = xcalloc(n, sizeof(int));
    for (int i = 0; i < m; i++) {
        int a = eu[i], b = ev[i];
        nbr[off[a] + fill[a]] = b; wt[off[a] + fill[a]++] = ew[i];
        nbr[off[b] + fill[b]] = a; wt[off[b] + fill[b]++] = ew[i];
    }
    free(fill); free(deg); free(eu); free(ev); free(ew);
    G *g = g_new(n, off, nbr, wt);
    if (g->gmax > GAIN_LIMIT) { fprintf(stderr, "a weighted degree exceeds 2^24\n"); return 3; }
    elite = xmalloc(sizeof(int8_t *) * prm.pool); elite_cut = xmalloc(sizeof(long) * prm.pool);
    for (int i = 0; i < prm.pool; i++) elite[i] = xmalloc(n);
    stackv = xmalloc(sizeof(int) * n); mark = xmalloc(sizeof(int) * n);
    uf_p = xmalloc(sizeof(int) * n); uf_sz = xmalloc(sizeof(int) * n); cid = xmalloc(sizeof(int) * n);
    cof = xmalloc(sizeof(int) * n); uf_x = xmalloc(n); cpar = xmalloc(n); tri = xmalloc(sizeof(Tri) * (size_t)m);
    best = xmalloc(n);
    best_cut = LONG_MIN;
    nv = n; NL = rex.levels; NR = 2 * NL;
    int L = NL, R = NR;
    double wbar = 0;
    for (int k = 0; k < 2 * m; k++) wbar += labs(wt[k]);
    wbar = m ? wbar / (2.0 * m) : 1.0;
    Tl = xmalloc(sizeof(double) * L); L0l = xmalloc(sizeof(double) * L);
    double tmin = 0.5 * wbar, tmax = rex.tmax * wbar * sqrt((double)n);
    if (tmax < tmin) tmax = tmin;
    for (int l = 0; l < L; l++) {
        double f = L > 1 ? (double)l / (L - 1) : 0.0;
        Tl[l] = tmin * pow(tmax / tmin, f);
        L0l[l] = prm.L0 * pow(rex.L0hot / prm.L0, f);
    }
    rp = xmalloc(sizeof(Rep) * R);
    slot = xmalloc(sizeof(int) * R);
    for (int r = 0; r < R; r++) {
        rp[r].g = r == 0 ? g : g_new(n, off, nbr, wt);
        G *h = rp[r].g;
        for (int v = 0; v < n; v++) h->s[v] = rnd() & 1;
        compute_all(h);
        ascend(h);
        walk_init(&rp[r].w, h);
        slot[r] = r;
        walk_level(&rp[r].w, h, L0l[r / 2]);
        pool_offer(h);
        if (h->cut > best_cut) { best_cut = h->cut; memcpy(best, h->s, n); }
    }
    since = 0; pass = 0;
    while (!out_of_time()) { pass++; run_list(first_item); }
    printf("o %ld\nv ", best_cut);
    for (int v = 0; v < n; v++) putchar('0' + best[v]);
    putchar('\n');
    return 0;
}
