/*
 * mcx2: a weighted max-cut engine that mixes several physics principles (B20_R125; `candidate_kinds/mcx2.py`).
 *
 * It is mcx (B20_R104; every function of `mcx.c` is kept as it was) turned into an interpreter: the search is a
 * PROGRAM over physics operators, acting on a population of replicas at LEVELS temperatures (two replicas per level).
 * The program is the body of a loop that repeats until the CPU budget is spent. Its statements:
 *   B<k>   every replica runs k attractors of breakout local search (Benlic and Hao 2013): an adaptive perturbation
 *          then steepest ascent, the zero-temperature refinement; its perturbation strength is its level's
 *   b<k>   the same for the two replicas of the coldest level only
 *   X      replica exchange (parallel tempering: Swendsen and Wang 1986; Hukushima and Nemoto 1996): adjacent levels
 *          swap states with probability min(1, exp((1/T_l - 1/T_l+1)(cut_l+1 - cut_l)))
 *   I      isoenergetic cluster moves (Houdayer 2001; Zhu, Ochoa and Katzgraber 2015): at each level the two replicas
 *          are aligned (a cut and its complement are the same cut), and one connected cluster where they disagree is
 *          exchanged between them; the sum of the two cuts is unchanged, each replica jumps a whole domain, then both
 *          descend. A cluster larger than n / 2 is not exchanged
 *   C      renormalisation (mcx -rs 2): the coldest replica is replaced by a coarse-grained search of what the shared
 *          elite pool does not agree on, projected back and polished
 *   M      MACUT's multi-parent grouping crossover (Wu and Hao 2012) of the elite pool into the hottest replica
 *   H      Houdayer's exchange of two elites (mcx -rs 1) into the hottest replica
 *   R      the hottest replica restarts from a random cut
 *   S<k>   the next statement runs only after k attractors (in all) without a new best; running it restarts the
 *          count (a stall-triggered move)
 *   P<k>   the next statement runs only on every k-th pass through the loop
 * A program has 1 to 32 statements and at least one B or b. Level temperatures are in cut units, geometric from
 * 0.5 x the mean |weight| up to TMAX x the mean |weight| x sqrt(n); perturbation strengths geometric from L0 (coldest)
 * to L0HOT (hottest). All replicas share mcx's elite pool. The default program, the builder's hybrid ("REX"), is
 * "B100 X I S2000 C": the human-designed baseline for the system's own programs.
 * None of the operators is new; the language and the default are the builder's, made at Daniel's request
 * (24 Oct 2026). Whether any program is better is a matter of measurement.
 *
 * Input (stdin):  "n m seed budget_ms\n" then m lines "u v w" (0-based, u != v, w a non-zero integer).
 * Output (stdout): "o <best cut>\n" and "v <n characters 0/1>\n" (the side of every vertex).
 * Exit 2: malformed input or options; exit 3: a weighted degree too large for bucketed gains (> 2^24).
 * Options (data only): mcx's -L0 -P -tt -pool -pert (-restart and -rs are accepted and unused: stalls are the
 * program's S statements), -levels <1..8> -tmax <frac> -L0hot <frac> and -prog "<statements>".
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
typedef struct { char op; long arg; } Ins;
static Ins prog[32];
static int nprog;
static const char *DEFAULT_PROG = "B100 X I S2000 C";


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

static int parse_prog(const char *s) {
    nprog = 0;
    int has_b = 0;
    while (*s) {
        while (*s == ' ' || *s == ',') s++;
        if (!*s) break;
        char op = *s++;
        if (!strchr("BbXICMHRSP", op) || nprog >= 32) return 0;
        long arg = 0; int digits = 0;
        while (*s >= '0' && *s <= '9') { arg = arg * 10 + (*s++ - '0'); if (++digits > 9) return 0; }
        int needs = strchr("BbSP", op) != NULL;
        if (needs != (digits > 0) || (needs && arg < 1)) return 0;
        if (*s && *s != ' ' && *s != ',') return 0;
        if (op == 'B' || op == 'b') has_b = 1;
        prog[nprog].op = op; prog[nprog++].arg = arg;
    }
    return nprog > 0 && has_b;
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
    int8_t *best = xmalloc(n);
    long best_cut = LONG_MIN;
    int L = rex.levels, R = 2 * L;
    double wbar = 0;
    for (int k = 0; k < 2 * m; k++) wbar += labs(wt[k]);
    wbar = m ? wbar / (2.0 * m) : 1.0;
    double *T = xmalloc(sizeof(double) * L), *L0l = xmalloc(sizeof(double) * L);
    double tmin = 0.5 * wbar, tmax = rex.tmax * wbar * sqrt((double)n);
    if (tmax < tmin) tmax = tmin;
    for (int l = 0; l < L; l++) {
        double f = L > 1 ? (double)l / (L - 1) : 0.0;
        T[l] = tmin * pow(tmax / tmin, f);
        L0l[l] = prm.L0 * pow(rex.L0hot / prm.L0, f);
    }
    Rep *rp = xmalloc(sizeof(Rep) * R);
    int *slot = xmalloc(sizeof(int) * R);          /* slot[2 l + k]: the replica at level l, place k */
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
    long since = 0, pass = 0;                       /* attractors in all since the last new best; loop passes */
#define NOTE(h) do { pool_offer(h); if ((h)->cut > best_cut) { best_cut = (h)->cut; memcpy(best, (h)->s, n); since = 0; } } while (0)
    while (!out_of_time()) {
        pass++;
        int skip = 0;
        for (int pc = 0; pc < nprog && !out_of_time(); pc++) {
            Ins in = prog[pc];
            if (skip) { skip = 0; continue; }
            if (in.op == 'S') { if (since >= in.arg) since = 0; else skip = 1; continue; }
            if (in.op == 'P') { if (pass % in.arg) skip = 1; continue; }
            if (in.op == 'B' || in.op == 'b') {
                int qn = in.op == 'B' ? R : 2;
                for (int q = 0; q < qn && !out_of_time(); q++) {
                    Rep *x = &rp[slot[q]];
                    for (long i = 0; i < in.arg && !out_of_time(); i++) {
                        long rb = best_cut;
                        perturb(x->g, &x->w, best, &rb);
                        ascend(x->g);
                        Walk *w = &x->w; G *h = x->g;
                        if (h->cut == w->last_cut && memcmp(h->s, w->last_opt, n) == 0) { if (++w->L > w->Lmax) w->L = w->Lmax; }
                        else { w->L = w->Lmin; w->last_cut = h->cut; memcpy(w->last_opt, h->s, n); }
                        if (rb > best_cut) {                     /* a new best was seen during the perturbation */
                            best_cut = rb; if (h->cut == rb) memcpy(best, h->s, n); since = 0; w->omega = 0;
                        } else if (h->cut > best_cut) { best_cut = h->cut; memcpy(best, h->s, n); since = 0; w->omega = 0; }
                        else { since++; if (++w->omega > BLS_T && prm.pert == 2) { w->omega = 0; w->strong = 1; } }
                        pool_offer(h);
                    }
                }
            } else if (in.op == 'X') {
                for (int l = 0; l + 1 < L; l++)
                    for (int k = 0; k < 2; k++) {
                        int a = slot[2 * l + k], b = slot[2 * (l + 1) + k];
                        double d = (1.0 / T[l] - 1.0 / T[l + 1]) * (double)(rp[b].g->cut - rp[a].g->cut);
                        if (d >= 0 || rnd01() < exp(d)) {
                            slot[2 * l + k] = b; slot[2 * (l + 1) + k] = a;
                            walk_level(&rp[b].w, rp[b].g, L0l[l]); walk_level(&rp[a].w, rp[a].g, L0l[l + 1]);
                        }
                    }
            } else if (in.op == 'I') {
                for (int l = 0; l < L && !out_of_time(); l++) {
                    G *ga = rp[slot[2 * l]].g, *gb = rp[slot[2 * l + 1]].g;
                    if (icm_move(ga, gb)) { ascend(ga); ascend(gb); NOTE(ga); NOTE(gb); }
                }
            } else if (in.op == 'C') {
                G *h = rp[slot[0]].g;
                if (elites >= 2 && coarse_step(h)) { NOTE(h); walk_level(&rp[slot[0]].w, h, L0l[0]); }
            } else {                                     /* M, H, R act on the hottest replica */
                int q = slot[2 * (L - 1)];
                G *h = rp[q].g;
                if (in.op == 'R') for (int v = 0; v < n; v++) h->s[v] = rnd() & 1;
                else if (elites < 2) continue;
                else if (in.op == 'M') macut_crossover(h);
                else { int a = (int)(rnd() % elites), b = (int)(rnd() % (elites - 1)); if (b >= a) b++; cluster_exchange(h, a, b); }
                compute_all(h); ascend(h); NOTE(h);
                walk_level(&rp[q].w, h, L0l[L - 1]);
            }
        }
    }
    printf("o %ld\nv ", best_cut);
    for (int v = 0; v < n; v++) putchar('0' + best[v]);
    putchar('\n');
    return 0;
}
