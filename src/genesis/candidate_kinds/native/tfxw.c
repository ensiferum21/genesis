/* tfxw-v1: the largest triangle-free subgraph of a host graph with up to 1024 vertices, anytime, one core.
 *
 * tfx-v1's search (B20_R88; B20_R89 chose its configuration), rebuilt so that it scales past 64 vertices:
 *   - vertex sets are arrays of W = ceil(n / 64) words instead of one word;
 *   - every member keeps, for every host edge, its tightness t[e]: the number of triangles that e would close with
 *     two edges of the member (the number of common neighbours of e's endpoints in the member). An edge outside the
 *     member is free when t = 0 and 1-tight when t = 1. Adding or removing an edge (u, v) changes t only on host
 *     edges (u, w) and (v, w) for w adjacent to the other endpoint in the member, so it costs O(W + degree)
 *     (the tightness technique of Andrade, Resende and Werneck, J. Heuristics 2012, on the triangle hypergraph);
 *   - (1,2)-swaps run from a work list: after a perturbation only the member's edges near the touched vertices are
 *     re-examined, not all of them (local search confined to the perturbation, as in ARW's iterated local search);
 *   - a rejected iteration is undone from a log of its additions and removals instead of copying the member back;
 *   - kicks sample the forced-in edge instead of listing every unchosen edge.
 * Every operator of tfx-v1 is kept with the same parameters and meaning (warm starts: discrete simulated bifurcation,
 * cut descent, three-body mean-field annealing; then iterated local search with acceptance by probability or
 * Metropolis with replica exchange, crossover, an edge-frequency memory, path relinking and restarts); see tfx.c.
 * Mean-field annealing needs the host's triangle lists; above TRI_CAP entries it is switched off (reported).
 *
 * stdin:  n m seed budget_ms, then m lines "u v" (0 <= u < v < n).   argv: key=value parameters (as tfx-v1).
 * stdout: "c" statistics, "v <m chars 0/1>" (the best edge set, in input order), "s <size>".
 * Exit 2 on malformed input or an unknown parameter, 3 when memory runs out.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef uint64_t u64;
#define MAXN 1024
#define POOLMAX 64
#define MAXK 32
#define TRI_CAP 40000000LL

static int n, m, W;
static int *eu, *ev, *eidm, *deg, *ioff, *ilist;
static u64 *A;
#define ROW(M, v) ((M) + (size_t)(v) * W)

static double FRAC = 0.3, PW = 0.1, TMIN = 0.3, TMAX = 2.0, RHO = 0.0, PHERW = 0.0, FEMLAM = 1.5;
static int K = 4, ACC = 0, XCHG = 50, CROSS = 0, WS = 3, REPL = 32, STEPS = 400, KICKS = 1, FEMSTEPS = 300;
static int RESTART = 0, RELINK = 0;
static double FEMLR = 0.0, DESC_SHARE = 0.5;

static u64 rs[2];
static inline u64 rnd64(void) {
    u64 s1 = rs[0];
    const u64 s0 = rs[1];
    rs[0] = s0;
    s1 ^= s1 << 23;
    rs[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
    return rs[1] + s0;
}
static inline unsigned rndn(unsigned k) { return (unsigned)(((rnd64() >> 32) * (u64)k) >> 32); }
static inline double rndu(void) { return (rnd64() >> 11) * (1.0 / 9007199254740992.0); }
static double cpu_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t);
    return t.tv_sec * 1e3 + t.tv_nsec / 1e6;
}
static inline int ctz(u64 x) { return __builtin_ctzll(x); }
static inline int pc(u64 x) { return __builtin_popcountll(x); }
static void *xcalloc(size_t k, size_t s) {
    void *p = calloc(k ? k : 1, s);
    if (!p) exit(3);
    return p;
}
static inline int eid(int u, int v) { return eidm[(size_t)u * n + v]; }

/* ---------- members ---------- */
typedef struct {
    u64 *N;              /* n x W: the member's adjacency */
    unsigned char *in;   /* m */
    int *t;              /* m: tightness */
    int size;
} Sol;

static Sol s_new(void) {
    Sol S;
    S.N = xcalloc((size_t)n * W, sizeof(u64));
    S.in = xcalloc(m, 1);
    S.t = xcalloc(m, sizeof(int));
    S.size = 0;
    return S;
}
static void s_clear(Sol *S) {
    memset(S->N, 0, (size_t)n * W * sizeof(u64));
    memset(S->in, 0, m);
    memset(S->t, 0, (size_t)m * sizeof(int));
    S->size = 0;
}

/* the undo log of the current iteration: +i added, -(i+1) removed */
static int *ulog, ulen, ucap, logging;
static inline void u_push(int x) {
    if (!logging) return;
    if (ulen == ucap) {
        ucap = ucap ? 2 * ucap : 1024;
        ulog = realloc(ulog, (size_t)ucap * sizeof(int));
        if (!ulog) exit(3);
    }
    ulog[ulen++] = x;
}

/* t changes for the host edges (x, w), w a member neighbour of y, by d */
static inline void bump(Sol *S, int x, int y, int d) {
    const u64 *r = ROW(S->N, y);
    for (int k = 0; k < W; k++) {
        u64 b = r[k];
        while (b) {
            int w = (k << 6) | ctz(b);
            b &= b - 1;
            if (w == x) continue;
            int j = eid(x, w);
            if (j >= 0) S->t[j] += d;
        }
    }
}
static void s_add(Sol *S, int i) {
    int u = eu[i], v = ev[i];
    bump(S, v, u, +1);
    bump(S, u, v, +1);
    ROW(S->N, u)[v >> 6] |= 1ULL << (v & 63);
    ROW(S->N, v)[u >> 6] |= 1ULL << (u & 63);
    S->in[i] = 1;
    S->size++;
    u_push(i);
}
static void s_rem(Sol *S, int i) {
    int u = eu[i], v = ev[i];
    ROW(S->N, u)[v >> 6] &= ~(1ULL << (v & 63));
    ROW(S->N, v)[u >> 6] &= ~(1ULL << (u & 63));
    bump(S, v, u, -1);
    bump(S, u, v, -1);
    S->in[i] = 0;
    S->size--;
    u_push(-(i + 1));
}
static void undo(Sol *S) {
    int was = logging;
    logging = 0;
    for (int q = ulen - 1; q >= 0; q--) {
        int x = ulog[q];
        if (x >= 0) s_rem(S, x); else s_add(S, -x - 1);
    }
    ulen = 0;
    logging = was;
}
static inline int s_free(const Sol *S, int i) { return !S->in[i] && S->t[i] == 0; }

static void shuffle(int *a, int k) {
    for (int i = k - 1; i > 0; i--) {
        int j = rndn(i + 1), t = a[i];
        a[i] = a[j];
        a[j] = t;
    }
}
static double *tau, *key;
static int cmp_key(const void *x, const void *y) {
    double a = key[*(const int *)x], b = key[*(const int *)y];
    return a < b ? 1 : a > b ? -1 : 0;
}
static int *cbuf, *cbuf2;
static void fill_list(Sol *S, int *a, int k) {
    if (PHERW > 0) {
        for (int i = 0; i < k; i++) key[a[i]] = PHERW * tau[a[i]] + rndu();
        qsort(a, k, sizeof(int), cmp_key);
    } else
        shuffle(a, k);
    for (int i = 0; i < k; i++)
        if (s_free(S, a[i])) s_add(S, a[i]);
}
static void fill_all(Sol *S) {
    int k = 0;
    for (int i = 0; i < m; i++)
        if (s_free(S, i)) cbuf[k++] = i;
    fill_list(S, cbuf, k);
}
static unsigned char *vmark;
static void fill_verts(Sol *S, const int *vs, int nv) {
    int k = 0;
    for (int q = 0; q < nv; q++) {
        int x = vs[q];
        for (int p = ioff[x]; p < ioff[x + 1]; p++) {
            int i = ilist[p];
            if (s_free(S, i) && !vmark[i]) {
                vmark[i] = 1;
                cbuf[k++] = i;
            }
        }
    }
    for (int q = 0; q < k; q++) vmark[cbuf[q]] = 0;
    fill_list(S, cbuf, k);
}

/* ---------- best ---------- */
static unsigned char *best_in;
static int best_size = -1, *best_list, best_n;
static double t_best;
static long long st_swaps, st_iters, st_cross_ok, st_cross, st_xchg, st_starts, st_restarts;
static void offer_best(const Sol *S) {
    if (S->size > best_size) {
        best_size = S->size;
        memcpy(best_in, S->in, m);
        best_n = 0;
        for (int i = 0; i < m; i++)
            if (S->in[i]) best_list[best_n++] = i;
        t_best = cpu_ms();
        if (RHO > 0)
            for (int i = 0; i < m; i++) tau[i] = (1 - RHO) * tau[i] + RHO * S->in[i];
    }
}

/* ---------- (1,2)-swaps from a work list of member edges ---------- */
static int *wl, wlen;
static unsigned char *inwl;
static inline void wl_push(const Sol *S, int e) {
    if (S->in[e] && !inwl[e]) {
        inwl[e] = 1;
        wl[wlen++] = e;
    }
}
static void wl_push_vertex(const Sol *S, int x) {
    const u64 *r = ROW(S->N, x);
    for (int k = 0; k < W; k++) {
        u64 b = r[k];
        while (b) {
            int w = (k << 6) | ctz(b);
            b &= b - 1;
            wl_push(S, eid(x, w));
        }
    }
}
static void wl_all(const Sol *S) {
    for (int i = 0; i < m; i++) wl_push(S, i);
}
static void wl_clear(void) {
    for (int q = 0; q < wlen; q++) inwl[wl[q]] = 0;
    wlen = 0;
}
/* the 1-tight edges blocked only by e = (a, b): (a, x) for x a member neighbour of b, and (b, x) for x of a */
static int cands(const Sol *S, int a, int b, int *c) {
    int nc = 0;
    for (int side = 0; side < 2; side++) {
        int p = side ? b : a, q = side ? a : b;
        const u64 *r = ROW(S->N, q);
        for (int k = 0; k < W; k++) {
            u64 bits = r[k];
            while (bits) {
                int x = (k << 6) | ctz(bits);
                bits &= bits - 1;
                if (x == p) continue;
                int j = eid(p, x);
                if (j >= 0 && !S->in[j] && S->t[j] == 1) c[nc++] = j;
            }
        }
    }
    return nc;
}
static int *cand;
static int swaps(Sol *S, double deadline) {
    int applied = 0;
    long long steps = 0;
    while (wlen > 0) {
        int q = rndn(wlen), e = wl[q];
        wl[q] = wl[--wlen];
        inwl[e] = 0;
        if (!S->in[e]) continue;
        if ((++steps & 1023) == 0 && cpu_ms() >= deadline) break;
        int a = eu[e], b = ev[e];
        int nc = cands(S, a, b, cand);
        if (nc < 2) continue;
        s_rem(S, e);
        shuffle(cand, nc);
        int done = 0;
        for (int x = 0; x < nc && !done; x++) {
            s_add(S, cand[x]);
            for (int y = x + 1; y < nc; y++)
                if (s_free(S, cand[y])) {
                    s_add(S, cand[y]);
                    int vs[6] = {a, b, eu[cand[x]], ev[cand[x]], eu[cand[y]], ev[cand[y]]};
                    fill_verts(S, vs, 6);
                    for (int z = 0; z < 6; z++) wl_push_vertex(S, vs[z]);
                    done = 1;
                    break;
                }
            if (!done) s_rem(S, cand[x]);
        }
        if (done)
            applied++;
        else
            s_add(S, e);
    }
    wl_clear();
    st_swaps += applied;
    return applied;
}
static void local_search_all(Sol *S, double deadline) {
    wl_all(S);
    swaps(S, deadline);
}

/* force in an unchosen edge (sampled; a best-solution edge with probability relink%, or the best-pheromone of three),
   removing one edge at each blocker, then refill and search locally */
static int sample_out(const Sol *S) {
    for (int tries = 0; tries < 64; tries++) {
        int i = rndn(m);
        if (!S->in[i]) return i;
    }
    int k = 0;
    for (int i = 0; i < m; i++)
        if (!S->in[i]) cbuf2[k++] = i;
    return k ? cbuf2[rndn(k)] : -1;
}
static void kick(Sol *S) {
    int i = sample_out(S);
    if (i < 0) return;
    if (RELINK > 0 && (int)rndn(100) < RELINK && best_n > 0) {
        for (int tries = 0; tries < 64; tries++) {
            int j = best_list[rndn(best_n)];
            if (!S->in[j]) {
                i = j;
                break;
            }
        }
    } else if (PHERW > 0)
        for (int r = 0; r < 2; r++) {
            int j = sample_out(S);
            if (j >= 0 && tau[j] > tau[i]) i = j;
        }
    int u = eu[i], v = ev[i];
    int *touched = cbuf2, nt = 0;
    touched[nt++] = u;
    touched[nt++] = v;
    const u64 *ru = ROW(S->N, u), *rv = ROW(S->N, v);
    for (int k = 0; k < W; k++) {
        u64 b = ru[k] & rv[k];
        while (b) {
            int w = (k << 6) | ctz(b);
            b &= b - 1;
            int x = rndu() < 0.5 ? u : v;
            s_rem(S, eid(x, w));
            touched[nt++] = w;
        }
    }
    s_add(S, i);
    int vs[MAXN];
    int nv = nt < MAXN ? nt : MAXN;
    memcpy(vs, touched, nv * sizeof(int));
    fill_verts(S, vs, nv);
    for (int z = 0; z < nv; z++) wl_push_vertex(S, vs[z]);
}

/* ---------- phase 1 ---------- */
typedef struct {
    u64 h;                 /* a key: the cut side's hash, or the edge set's hash */
    unsigned char *in;
    int size;
} Entry;
static Entry pool[POOLMAX];
static int npool;
static Sol scratch;

static u64 hash_bytes(const unsigned char *p, int k, u64 h) {
    for (int i = 0; i < k; i++) h = (h ^ p[i]) * 1099511628211ULL;
    return h;
}
static int cmp_pool(const void *x, const void *y) { return ((const Entry *)y)->size - ((const Entry *)x)->size; }
static void pool_trim(void) {
    qsort(pool, npool, sizeof(Entry), cmp_pool);
    for (int i = K; i < npool; i++) free(pool[i].in);
    if (npool > K) npool = K;
}
static void pool_offer(const Sol *S, u64 h) {
    for (int i = 0; i < npool; i++)
        if (pool[i].h == h) return;
    if (npool == POOLMAX) pool_trim();
    pool[npool].h = h;
    pool[npool].in = xcalloc(m, 1);
    memcpy(pool[npool].in, S->in, m);
    pool[npool].size = S->size;
    npool++;
    offer_best(S);
    st_starts++;
}
static u64 *sidebuf, *posbuf;
static void complete_cut(const u64 *side, Sol *S) {
    s_clear(S);
    for (int i = 0; i < m; i++)
        if (((side[eu[i] >> 6] >> (eu[i] & 63)) & 1) != ((side[ev[i] >> 6] >> (ev[i] & 63)) & 1)) s_add(S, i);
    fill_all(S);
}
static void offer_side(u64 *side) {
    int last = n & 63;
    if (last) side[W - 1] &= (1ULL << last) - 1;
    if (side[0] & 1)
        for (int k = 0; k < W; k++) side[k] = ~side[k];
    if (last) side[W - 1] &= (1ULL << last) - 1;
    u64 h = hash_bytes((const unsigned char *)side, W * 8, 1469598103934665603ULL) & ~(1ULL << 63);
    for (int i = 0; i < npool; i++)
        if (pool[i].h == h) return;
    complete_cut(side, &scratch);
    pool_offer(&scratch, h);
}
static void offer_sol(const Sol *S) {
    u64 h = hash_bytes(S->in, m, 1469598103934665603ULL) | (1ULL << 63);
    pool_offer(S, h);
}

static double *xs, *ys;
static int dsb_batch(double deadline) {
    double rms = sqrt(2.0 * m / (n * (n - 1.0))), c0 = 0.5 / (rms * sqrt((double)n)), A0 = 1.0, DT = 0.5;
    int R = REPL > 64 ? 64 : REPL, stopped = 0;
    for (int r = 0; r < R; r++)
        for (int i = 0; i < n; i++) {
            xs[r * n + i] = -0.1 + 0.2 * rndu();
            ys[r * n + i] = -0.1 + 0.2 * rndu();
        }
    for (int k = 0; k < STEPS; k++) {
        double a = A0 - A0 * k / STEPS;
        for (int r = 0; r < R; r++) {
            double *x = xs + r * n, *y = ys + r * n;
            memset(posbuf, 0, W * sizeof(u64));
            for (int i = 0; i < n; i++)
                if (x[i] > 0) posbuf[i >> 6] |= 1ULL << (i & 63);
            for (int i = 0; i < n; i++) {
                const u64 *ai = ROW(A, i);
                int c = 0;
                for (int w = 0; w < W; w++) c += pc(ai[w] & posbuf[w]);
                y[i] += DT * (-a * x[i] + c0 * (-(2.0 * c - deg[i])));
            }
            for (int i = 0; i < n; i++) {
                x[i] += DT * A0 * y[i];
                if (fabs(x[i]) > 1.0) {
                    x[i] = x[i] > 0 ? 1.0 : -1.0;
                    y[i] = 0.0;
                }
            }
        }
        if (k % 10 == 9 && cpu_ms() >= deadline) {
            stopped = 1;
            break;
        }
    }
    for (int r = 0; r < R; r++) {
        memset(sidebuf, 0, W * sizeof(u64));
        for (int i = 0; i < n; i++)
            if (xs[r * n + i] > 0) sidebuf[i >> 6] |= 1ULL << (i & 63);
        offer_side(sidebuf);
    }
    return stopped;
}

static int *perm;
static void descent_side(u64 *side) {
    memset(side, 0, W * sizeof(u64));
    for (int i = 0; i < n; i++)
        if (rndu() < 0.5) side[i >> 6] |= 1ULL << (i & 63);
    for (int i = 0; i < n; i++) perm[i] = i;
    int improved = 1;
    while (improved) {
        improved = 0;
        shuffle(perm, n);
        for (int t = 0; t < n; t++) {
            int v = perm[t], mine = (side[v >> 6] >> (v & 63)) & 1, same = 0;
            const u64 *av = ROW(A, v);
            for (int w = 0; w < W; w++) same += pc(av[w] & (mine ? side[w] : ~side[w]));
            if (2 * same > deg[v]) {
                side[v >> 6] ^= 1ULL << (v & 63);
                improved = 1;
            }
        }
    }
}
static void descent_one(void) {
    descent_side(sidebuf);
    offer_side(sidebuf);
}

static double *pe, *hf, *gf;
static long long *tri_off;
static int *tri_ff, *tri_gg;
static void fem_grad(void) {
    for (int i = 0; i < m; i++) {
        hf[i] = 0.2 * (rndu() - 0.5);
        pe[i] = 1.0 / (1.0 + exp(-hf[i]));
    }
    double t0 = 1.0, t1 = 0.01;
    for (int k = 0; k < FEMSTEPS; k++) {
        double temp = t0 * pow(t1 / t0, (double)k / (FEMSTEPS - 1)), norm = 0;
        for (int i = 0; i < m; i++) {
            double s = 0;
            for (long long q = tri_off[i]; q < tri_off[i + 1]; q++) s += pe[tri_ff[q]] * pe[tri_gg[q]];
            gf[i] = -1.0 + FEMLAM * s + temp * hf[i];
            norm += gf[i] * gf[i];
        }
        norm = sqrt(norm / m) + 1e-12;
        for (int i = 0; i < m; i++) {
            hf[i] -= FEMLR * gf[i] / norm;
            pe[i] = hf[i] > 30 ? 1.0 : hf[i] < -30 ? 0.0 : 1.0 / (1.0 + exp(-hf[i]));
        }
    }
}
static void fem_one(void) {
    if (FEMLR > 0)
        fem_grad();
    else {
        for (int i = 0; i < m; i++) pe[i] = 0.3 + 0.4 * rndu();
        double t0 = 2.0, t1 = 0.02, eta = 0.5;
        for (int k = 0; k < FEMSTEPS; k++) {
            double temp = t0 * pow(t1 / t0, (double)k / (FEMSTEPS - 1));
            for (int i = 0; i < m; i++) {
                double s = 0;
                for (long long q = tri_off[i]; q < tri_off[i + 1]; q++) s += pe[tri_ff[q]] * pe[tri_gg[q]];
                double h = (1.0 - FEMLAM * s) / temp;
                double target = h > 30 ? 1.0 : h < -30 ? 0.0 : 1.0 / (1.0 + exp(-h));
                pe[i] = (1 - eta) * pe[i] + eta * target;
            }
        }
    }
    s_clear(&scratch);
    for (int i = 0; i < m; i++) {
        cbuf[i] = i;
        key[i] = pe[i] + 1e-6 * rndu();
    }
    qsort(cbuf, m, sizeof(int), cmp_key);
    for (int i = 0; i < m; i++)
        if (s_free(&scratch, cbuf[i])) s_add(&scratch, cbuf[i]);
    offer_sol(&scratch);
}

/* ---------- phase 2 ---------- */
static Sol mem[MAXK];
static double temp_of[MAXK];
static int accept(int j, int newsize, int oldsize) {
    if (newsize >= oldsize) return 1;
    if (ACC == 0) return rndu() < PW;
    return rndu() < exp((newsize - oldsize) / temp_of[j]);
}
static int same_set(const Sol *a, const Sol *b) { return a->size == b->size && !memcmp(a->in, b->in, m); }
static void crossover(int k, double deadline) {
    int a = rndn(k), b = rndn(k - 1);
    if (b >= a) b++;
    s_clear(&scratch);
    for (int i = 0; i < m; i++)
        if (mem[a].in[i] && mem[b].in[i]) s_add(&scratch, i);
    fill_all(&scratch);
    local_search_all(&scratch, deadline);
    offer_best(&scratch);
    st_cross++;
    int worst = 0;
    for (int j = 1; j < k; j++)
        if (mem[j].size < mem[worst].size) worst = j;
    if (scratch.size <= mem[worst].size) return;
    for (int j = 0; j < k; j++)
        if (same_set(&mem[j], &scratch)) return;
    Sol t = mem[worst];
    mem[worst] = scratch;
    scratch = t;
    st_cross_ok++;
}

int main(int argc, char **argv) {
    for (int a = 1; a < argc; a++) {
        char *eq = strchr(argv[a], '=');
        if (!eq) return 2;
        *eq = 0;
        const char *k = argv[a];
        double v = atof(eq + 1);
        if (!strcmp(k, "frac")) FRAC = v;
        else if (!strcmp(k, "K")) K = (int)v;
        else if (!strcmp(k, "pw")) PW = v;
        else if (!strcmp(k, "acc")) ACC = (int)v;
        else if (!strcmp(k, "tmin")) TMIN = v;
        else if (!strcmp(k, "tmax")) TMAX = v;
        else if (!strcmp(k, "xchg")) XCHG = (int)v;
        else if (!strcmp(k, "cross")) CROSS = (int)v;
        else if (!strcmp(k, "rho")) RHO = v;
        else if (!strcmp(k, "pherw")) PHERW = v;
        else if (!strcmp(k, "ws")) WS = (int)v;
        else if (!strcmp(k, "repl")) REPL = (int)v;
        else if (!strcmp(k, "steps")) STEPS = (int)v;
        else if (!strcmp(k, "kicks")) KICKS = (int)v;
        else if (!strcmp(k, "femsteps")) FEMSTEPS = (int)v;
        else if (!strcmp(k, "femlam")) FEMLAM = v;
        else if (!strcmp(k, "dshare")) DESC_SHARE = v;
        else if (!strcmp(k, "restart")) RESTART = (int)v;
        else if (!strcmp(k, "relink")) RELINK = (int)v;
        else if (!strcmp(k, "femlr")) FEMLR = v;
        else return 2;
    }
    if (K < 1 || K > MAXK || FEMSTEPS < 2) return 2;
    long long seed;
    double budget;
    if (scanf("%d %d %lld %lf", &n, &m, &seed, &budget) != 4 || n < 1 || n > MAXN || m < 0 ||
        (long long)m > (long long)n * (n - 1) / 2)
        return 2;
    double start = cpu_ms(), deadline = start + budget;
    W = (n + 63) / 64;
    eu = xcalloc(m, sizeof(int));
    ev = xcalloc(m, sizeof(int));
    eidm = xcalloc((size_t)n * n, sizeof(int));
    memset(eidm, -1, (size_t)n * n * sizeof(int));
    A = xcalloc((size_t)n * W, sizeof(u64));
    deg = xcalloc(n, sizeof(int));
    for (int i = 0; i < m; i++) {
        if (scanf("%d %d", &eu[i], &ev[i]) != 2) return 2;
        int u = eu[i], v = ev[i];
        if (u < 0 || v >= n || u >= v || eid(u, v) >= 0) return 2;
        eidm[(size_t)u * n + v] = eidm[(size_t)v * n + u] = i;
        ROW(A, u)[v >> 6] |= 1ULL << (v & 63);
        ROW(A, v)[u >> 6] |= 1ULL << (u & 63);
        deg[u]++;
        deg[v]++;
    }
    ioff = xcalloc(n + 1, sizeof(int));
    ilist = xcalloc(2 * (size_t)m + 1, sizeof(int));
    for (int v = 0; v < n; v++) ioff[v + 1] = ioff[v] + deg[v];
    {
        int *fillp = xcalloc(n, sizeof(int));
        for (int i = 0; i < m; i++) {
            ilist[ioff[eu[i]] + fillp[eu[i]]++] = i;
            ilist[ioff[ev[i]] + fillp[ev[i]]++] = i;
        }
        free(fillp);
    }
    rs[0] = (u64)seed * 0x9E3779B97F4A7C15ULL + 0x632BE59BD9B4E019ULL;
    rs[1] = rs[0] ^ 0xD1B54A32D192ED03ULL;
    for (int i = 0; i < 20; i++) rnd64();
    tau = xcalloc(m, sizeof(double));
    key = xcalloc(m, sizeof(double));
    for (int i = 0; i < m; i++) tau[i] = 0.5;
    cbuf = xcalloc(m + 1, sizeof(int));
    cbuf2 = xcalloc(m + MAXN + 1, sizeof(int));
    cand = xcalloc(2 * (size_t)n + 2, sizeof(int));
    vmark = xcalloc(m, 1);
    wl = xcalloc(m + 1, sizeof(int));
    inwl = xcalloc(m, 1);
    best_in = xcalloc(m, 1);
    best_list = xcalloc(m + 1, sizeof(int));
    sidebuf = xcalloc(W, sizeof(u64));
    posbuf = xcalloc(W, sizeof(u64));
    perm = xcalloc(n, sizeof(int));
    int R = REPL > 64 ? 64 : REPL;
    xs = xcalloc((size_t)R * n, sizeof(double));
    ys = xcalloc((size_t)R * n, sizeof(double));
    scratch = s_new();
    int fem_off = 0;
    if (m > 0 && (WS & 4)) {
        long long tot = 0;
        for (int i = 0; i < m; i++) {
            const u64 *ru = ROW(A, eu[i]), *rv = ROW(A, ev[i]);
            for (int w = 0; w < W; w++) tot += pc(ru[w] & rv[w]);
        }
        if (tot > TRI_CAP) {
            WS &= ~4;
            fem_off = 1;
        } else {
            tri_off = xcalloc(m + 1, sizeof(long long));
            tri_ff = xcalloc(tot + 1, sizeof(int));
            tri_gg = xcalloc(tot + 1, sizeof(int));
            pe = xcalloc(m, sizeof(double));
            hf = xcalloc(m, sizeof(double));
            gf = xcalloc(m, sizeof(double));
            long long q = 0;
            for (int i = 0; i < m; i++) {
                tri_off[i] = q;
                const u64 *ru = ROW(A, eu[i]), *rv = ROW(A, ev[i]);
                for (int w = 0; w < W; w++) {
                    u64 c = ru[w] & rv[w];
                    while (c) {
                        int x = (w << 6) | ctz(c);
                        c &= c - 1;
                        tri_ff[q] = eid(eu[i], x);
                        tri_gg[q] = eid(ev[i], x);
                        q++;
                    }
                }
            }
            tri_off[m] = q;
        }
    }
    if (m == 0) goto out;
    /* phase 1 */
    {
        double p1_end = start + FRAC * budget;
        int first = 1;
        while (first || cpu_ms() < p1_end) {
            first = 0;
            double t0 = cpu_ms();
            int stopped = 0;
            if (WS & 1) stopped = dsb_batch(p1_end);
            double spent = cpu_ms() - t0;
            if (WS & 4) {
                double until = cpu_ms() + (WS & 1 ? spent : 1.0);
                do fem_one(); while (cpu_ms() < until && cpu_ms() < p1_end);
            }
            if (WS & 2) {
                double until = cpu_ms() + ((WS & 1) ? spent * DESC_SHARE / (1 - DESC_SHARE) : 1.0);
                do descent_one(); while (cpu_ms() < until && cpu_ms() < p1_end);
            }
            if (npool > 4 * K) pool_trim();
            if (stopped || !(WS & 7)) break;
        }
        if (npool == 0) {
            s_clear(&scratch);
            fill_all(&scratch);
            offer_sol(&scratch);
        }
    }
    /* phase 2 */
    {
        qsort(pool, npool, sizeof(Entry), cmp_pool);
        int k = npool < K ? npool : K;
        for (int j = 0; j < k; j++) {
            mem[j] = s_new();
            for (int i = 0; i < m; i++)
                if (pool[j].in[i]) s_add(&mem[j], i);
            local_search_all(&mem[j], deadline);
            offer_best(&mem[j]);
            temp_of[j] = k > 1 ? TMIN * pow(TMAX / TMIN, (double)j / (k - 1)) : TMIN;
        }
        long long it = 0, stall[MAXK] = {0};
        int j = 0;
        while (cpu_ms() < deadline) {
            Sol *S = &mem[j];
            int old = S->size;
            logging = 1;
            ulen = 0;
            for (int q = 0; q < KICKS; q++) kick(S);
            swaps(S, deadline);
            logging = 0;
            offer_best(S);
            if (S->size > old) stall[j] = 0; else stall[j]++;
            if (!accept(j, S->size, old)) undo(S);
            ulen = 0;
            if (RESTART > 0 && stall[j] >= RESTART) {
                descent_side(sidebuf);
                complete_cut(sidebuf, S);
                local_search_all(S, deadline);
                offer_best(S);
                stall[j] = 0;
                st_restarts++;
            }
            it++;
            st_iters++;
            if (ACC == 1 && k > 1 && it % XCHG == 0) {
                for (int a = 0; a + 1 < k; a++) {
                    double d = (mem[a + 1].size - mem[a].size) * (1.0 / temp_of[a] - 1.0 / temp_of[a + 1]);
                    if (d >= 0 || rndu() < exp(d)) {
                        Sol t = mem[a];
                        mem[a] = mem[a + 1];
                        mem[a + 1] = t;
                        st_xchg++;
                    }
                }
            }
            if (CROSS > 0 && k > 1 && it % CROSS == 0) crossover(k, deadline);
            j = (j + 1) % k;
        }
    }
out:
    printf("c starts %lld iters %lld swaps %lld cross %lld/%lld xchg %lld restarts %lld t_best_ms %.1f fem_off %d\n",
           st_starts, st_iters, st_swaps, st_cross_ok, st_cross, st_xchg, st_restarts, t_best - start, fem_off);
    printf("v ");
    for (int i = 0; i < m; i++) putchar(best_size > 0 && best_in[i] ? '1' : '0');
    printf("\ns %d\n", best_size > 0 ? best_size : 0);
    return 0;
}
