/*
 * mcx: a weighted max-cut engine (B20_R104; `candidate_kinds/mcx.py`).
 *
 * Input (stdin):  "n m seed budget_ms\n" then m lines "u v w" (0-based, u != v, w a non-zero integer).
 * Output (stdout): "o <best cut>\n" and "v <n characters 0/1>\n" (the side of every vertex).
 * Exit 2: malformed input or options; exit 3: a weighted degree too large for bucketed gains (> 2^24).
 *
 * Search: an iterated tabu search in the spirit of breakout local search (Benlic and Hao 2013):
 *   - incremental flip gains in bucket lists (the best move in O(1) amortised);
 *   - steepest ascent to a local optimum, then a perturbation of L flips whose strength adapts: L grows when the
 *     search returns to the same local optimum and resets after a new one. With probability P (falling from 1 to P0
 *     over 1000 attractors without a new best) the flips are directed (the best non-tabu move; tenure 3 + a random
 *     number up to n / TT_DIV; a tabu move that gives a new best is allowed); otherwise (-pert 0) random flips, or
 *     (-pert 1) half the time recency-based flips (the least recently moved of 8 sampled vertices);
 *     -pert 2 follows breakout local search's own rules (Benlic and Hao 2013, Algorithms 1-3 and formula (2), as
 *     read from the authors' paper): P = max(exp(-w / T), P0) with w the local optima since the last new best and
 *     T = 1000; with probability P * Q (Q = 0.5) directed single flips (their M1), with P * (1 - Q) directed pairs
 *     (M2: the best non-tabu vertex of each side, both moved), otherwise random flips (M3); after T local optima
 *     without a new best one strong random perturbation and w = 0; descent moves are also made tabu;
 *   - an elite pool of POOL distinct local optima; after RESTART attractors without a new best, a restart (-rs):
 *       0  none;
 *       1  cluster exchange: the vertices where two elites disagree form clusters in the graph, and a random half
 *          of the clusters is taken from the second elite (Houdayer's move from spin-glass physics);
 *       2  renormalisation: every edge on whose relative orientation all the elites agree is contracted (a union-find
 *          with parity), the contracted graph is a weighted max-cut problem on the clusters, it is searched by the
 *          same iterated tabu search from the best elite for RESTART attractors without a new best, and the result
 *          is projected back and polished (a coarse-graining step that keeps what the elites agree on and searches
 *          only what they do not). When nothing contracts, a cluster exchange is made instead;
 *       3  the multi-parent grouping crossover of the memetic algorithm MACUT (Wu and Hao, PPSN 2012, as read from
 *          the authors' paper): m = 2, 3 or 4 distinct elites at random; the vertices are grouped by their pattern of
 *          sides across the parents; the largest group goes to one side, the second largest to the other, every
 *          other vertex to a random side (the groups all parents share are kept whole).
 * Options (data only): -L0 <frac> -P <prob> -tt <div> -pool <k> -restart <attractors> -rs <0..3> -pert <0|1|2>
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

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

static int opt(const char *name, const char *val) {
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
    else return 0;
    return 1;
}

int main(int argc, char **argv) {
    if (argc % 2 != 1) { fprintf(stderr, "options come in pairs\n"); return 2; }
    for (int i = 1; i + 1 < argc; i += 2)
        if (!opt(argv[i], argv[i + 1])) { fprintf(stderr, "bad option %s %s\n", argv[i], argv[i + 1]); return 2; }
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
    for (int v = 0; v < n; v++) g->s[v] = rnd() & 1;
    compute_all(g);
    ascend(g);
    long best_cut = g->cut; memcpy(best, g->s, n);
    pool_offer(g);
    Walk w; walk_init(&w, g);
    while (its(g, &w, best, &best_cut, prm.restart, 1)) {
        if (prm.rs == 0 || elites < 2) continue;
        if (prm.rs == 3) {
            macut_crossover(g);
            compute_all(g);
            ascend(g);
        } else if (!(prm.rs == 2 && coarse_step(g))) {
            int a = (int)(rnd() % elites), b = (int)(rnd() % (elites - 1)); if (b >= a) b++;
            cluster_exchange(g, a, b);
            compute_all(g);
            ascend(g);
        }
        if (g->cut > best_cut) { best_cut = g->cut; memcpy(best, g->s, n); w.since = 0; }
        pool_offer(g);
    }
    printf("o %ld\nv ", best_cut);
    for (int v = 0; v < n; v++) putchar('0' + best[v]);
    putchar('\n');
    return 0;
}
