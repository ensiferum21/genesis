/* tfx-v1 (B20_R88): the largest triangle-free subgraph of a host graph (n <= 64), anytime, one core.
 *
 * A population search on the problem itself (edge sets), with warm starts and operators drawn from physics, biology
 * and the independent-set literature; which of them run, and how, is data (key=value arguments), so a configuration
 * search can choose (B20_R89).
 *
 * Phase 1, warm starts, for frac of the budget, completed greedily to triangle-free edge sets; a pool keeps the K
 * best distinct ones. ws is a bitmask:
 *   1  discrete simulated bifurcation on the host's max-cut (Goto et al., Science Advances 2021): repl replicas,
 *      steps steps, a0 1, dt 0.5, c0 = 0.5 / (rms(J) sqrt(n)), inelastic walls;
 *   2  one-flip cut descent from random two-colourings (dshare: its share of the time when dSB also runs);
 *   4  three-body mean-field annealing on the edge variables (femlr = 0: damped mean-field iteration
 *      p_e = sigmoid((1 - femlam sum_T p_f p_g) / T); femlr > 0: normalised gradient steps on the variational free
 *      energy, after the free-energy machine, Shen et al., Nature Computational Science 2025), femsteps steps,
 *      rounded greedily by decreasing p.
 * Phase 2, until the deadline: each member gets (1,2)-swaps (Andrade, Resende and Werneck, J. Heuristics 2012, on the
 * hypergraph whose vertices are host edges and whose hyperedges are host triangles), then iterated local search
 * round-robin: kicks forced-in edges (removing one edge at each blocker), (1,2)-swaps, acceptance:
 *   acc 0: keep if no smaller, else with probability pw;
 *   acc 1: Metropolis at the member's own temperature (geometric ladder tmin..tmax), and every xchg iterations
 *          neighbouring temperatures exchange states (parallel tempering, Swendsen and Wang 1986, Hukushima and
 *          Nemoto 1996);
 *   cross c > 0: every c iterations the intersection of two members is refilled and improved and replaces the worst
 *          member if larger and new (a memetic algorithm; Moscato 1989);
 *   rho, pherw > 0: an edge-frequency memory of the best solutions (ant colony optimisation, Dorigo 1992) orders
 *          greedy fills (pherw * tau + noise) and picks the forced-in edge (best of three);
 *   relink r > 0: with probability r% a kick forces in an edge of the best solution (path relinking, Glover 1997);
 *   restart s > 0: a member that has not improved for s iterations restarts from a new cut descent.
 * The largest edge set seen is printed. The caller re-checks the witness.
 *
 * stdin:  n m seed budget_ms, then m lines "u v" (0 <= u < v < n).   argv: key=value parameters (see main).
 * stdout: "c" statistics, "v <m chars 0/1>" (the best edge set, in input order), "s <size>".
 * Exit 2 on malformed input or an unknown parameter.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef uint64_t u64;
#define MAXN 64
#define MAXM 2016
#define POOLMAX 64

static int n, m;
static int eu[MAXM], ev[MAXM];
static short eidm[MAXN][MAXN];
static u64 A[MAXN];
static int deg[MAXN];
static int inc[MAXN][MAXN], ninc[MAXN];

/* parameters */
static double FRAC = 0.3, PW = 0.1, TMIN = 0.3, TMAX = 2.0, RHO = 0.0, PHERW = 0.0, FEMLAM = 1.5;
static int K = 4, ACC = 0, XCHG = 50, CROSS = 0, WS = 3, REPL = 32, STEPS = 400, KICKS = 1, FEMSTEPS = 300;
static int RESTART = 0, RELINK = 0;
static double FEMLR = 0.0;
static double DESC_SHARE = 0.5;

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

typedef struct {
    u64 N[MAXN];
    unsigned char in[MAXM];
    int size;
} Sol;

static double tau[MAXM];
static Sol best;
static long long st_swaps, st_iters, st_cross_ok, st_cross, st_xchg, st_starts, st_restarts;
static double t_best;

static inline void s_add(Sol *S, int i) {
    S->N[eu[i]] |= 1ULL << ev[i];
    S->N[ev[i]] |= 1ULL << eu[i];
    S->in[i] = 1;
    S->size++;
}
static inline void s_rem(Sol *S, int i) {
    S->N[eu[i]] &= ~(1ULL << ev[i]);
    S->N[ev[i]] &= ~(1ULL << eu[i]);
    S->in[i] = 0;
    S->size--;
}
static inline int s_free(const Sol *S, int i) { return !S->in[i] && !(S->N[eu[i]] & S->N[ev[i]]); }
static void s_clear(Sol *S) { memset(S, 0, sizeof *S); }

static void shuffle(int *a, int k) {
    for (int i = k - 1; i > 0; i--) {
        int j = rndn(i + 1), t = a[i];
        a[i] = a[j];
        a[j] = t;
    }
}
static double key[MAXM];
static int cmp_key(const void *x, const void *y) {
    double a = key[*(const int *)x], b = key[*(const int *)y];
    return a < b ? 1 : a > b ? -1 : 0;
}
/* greedy fill over a candidate list: random order, or by pheromone plus noise */
static void fill_list(Sol *S, int *a, int k) {
    if (PHERW > 0) {
        for (int i = 0; i < k; i++) key[a[i]] = PHERW * tau[a[i]] + rndu();
        qsort(a, k, sizeof(int), cmp_key);
    } else
        shuffle(a, k);
    for (int i = 0; i < k; i++)
        if (s_free(S, a[i])) s_add(S, a[i]);
}
static int cbuf[MAXM];
static void fill_all(Sol *S) {
    int k = 0;
    for (int i = 0; i < m; i++)
        if (!S->in[i]) cbuf[k++] = i;
    fill_list(S, cbuf, k);
}
static void fill_verts(Sol *S, u64 mask) {
    int k = 0;
    while (mask) {
        int x = ctz(mask);
        mask &= mask - 1;
        for (int j = 0; j < ninc[x]; j++) {
            int i = inc[x][j];
            if (!S->in[i]) cbuf[k++] = i;
        }
    }
    fill_list(S, cbuf, k);
}

static void offer_best(const Sol *S) {
    if (S->size > best.size) {
        best = *S;
        t_best = cpu_ms();
        if (RHO > 0)
            for (int i = 0; i < m; i++) tau[i] = (1 - RHO) * tau[i] + RHO * S->in[i];
    }
}

/* (1,2)-swaps until none applies */
static int ord[MAXM];
static int swaps(Sol *S, double deadline) {
    for (int i = 0; i < m; i++) ord[i] = i;
    int applied = 0;
    for (;;) {
        shuffle(ord, m);
        int improved = 0;
        for (int t = 0; t < m; t++) {
            int e = ord[t];
            if (!S->in[e]) continue;
            int a = eu[e], b = ev[e];
            u64 ma = 1ULL << a, mb = 1ULL << b;
            int c[2 * MAXN], nc = 0;
            for (int j = 0; j < ninc[a]; j++) {
                int i = inc[a][j];
                if (!S->in[i] && (S->N[eu[i]] & S->N[ev[i]]) == mb) c[nc++] = i;
            }
            for (int j = 0; j < ninc[b]; j++) {
                int i = inc[b][j];
                if (!S->in[i] && (S->N[eu[i]] & S->N[ev[i]]) == ma) c[nc++] = i;
            }
            if (nc < 2) continue;
            s_rem(S, e);
            shuffle(c, nc);
            int done = 0;
            for (int x = 0; x < nc && !done; x++) {
                s_add(S, c[x]);
                for (int y = x + 1; y < nc; y++)
                    if (s_free(S, c[y])) {
                        s_add(S, c[y]);
                        fill_verts(S, ma | mb);
                        done = 1;
                        break;
                    }
                if (!done) s_rem(S, c[x]);
            }
            if (done) {
                improved = 1;
                applied++;
            } else
                s_add(S, e);
        }
        if (!improved || cpu_ms() >= deadline) break;
    }
    st_swaps += applied;
    return applied;
}

/* force in an unchosen edge (uniform, or the best-pheromone of three), removing one edge at each blocker */
static void kick(Sol *S) {
    int k = 0;
    for (int i = 0; i < m; i++)
        if (!S->in[i]) cbuf[k++] = i;
    if (!k) return;
    int i = cbuf[rndn(k)];
    if (RELINK > 0 && (int)rndn(100) < RELINK) {
        int kk = 0;
        for (int q = 0; q < k; q++)
            if (best.in[cbuf[q]]) cbuf[kk++] = cbuf[q];
        if (kk) i = cbuf[rndn(kk)];
    } else if (PHERW > 0)
        for (int r = 0; r < 2; r++) {
            int j = cbuf[rndn(k)];
            if (tau[j] > tau[i]) i = j;
        }
    int u = eu[i], v = ev[i];
    u64 b = S->N[u] & S->N[v], touched = (1ULL << u) | (1ULL << v);
    while (b) {
        int w = ctz(b);
        b &= b - 1;
        int x = rndu() < 0.5 ? u : v;
        s_rem(S, eidm[x][w]);
        touched |= 1ULL << w;
    }
    s_add(S, i);
    fill_verts(S, touched);
}

/* ---------- phase 1 ---------- */
typedef struct {
    u64 side;
    Sol s;
} Entry;
static Entry pool[POOLMAX];
static int npool;

static void complete_cut(u64 side, Sol *S) {
    s_clear(S);
    for (int i = 0; i < m; i++)
        if (((side >> eu[i]) & 1) != ((side >> ev[i]) & 1)) s_add(S, i);
    fill_all(S);
}
static int cmp_pool(const void *x, const void *y) { return ((const Entry *)y)->s.size - ((const Entry *)x)->s.size; }
static void offer_side(u64 side) {
    u64 all = n == 64 ? ~0ULL : ((1ULL << n) - 1);
    side &= all;
    if (side & 1) side = ~side & all;
    for (int i = 0; i < npool; i++)
        if (pool[i].side == side) return;
    if (npool == POOLMAX) {
        qsort(pool, npool, sizeof(Entry), cmp_pool);
        npool = K;
    }
    pool[npool].side = side;
    complete_cut(side, &pool[npool].s);
    offer_best(&pool[npool].s);
    npool++;
    st_starts++;
}
static void offer_sol(const Sol *S) {
    /* a start that is not a cut completion (mean-field): keyed by its edge set's hash */
    u64 h = 1469598103934665603ULL;
    for (int i = 0; i < m; i++) h = (h ^ S->in[i]) * 1099511628211ULL;
    h |= 1ULL << 63;     /* never equal to a cut side of n < 64 */
    for (int i = 0; i < npool; i++)
        if (pool[i].side == h) return;
    if (npool == POOLMAX) {
        qsort(pool, npool, sizeof(Entry), cmp_pool);
        npool = K;
    }
    pool[npool].side = h;
    pool[npool].s = *S;
    offer_best(S);
    npool++;
    st_starts++;
}

static double xs[64][MAXN], ys[64][MAXN];
static int dsb_batch(double deadline) {
    double rms = sqrt(2.0 * m / (n * (n - 1.0))), c0 = 0.5 / (rms * sqrt((double)n)), A0 = 1.0, DT = 0.5;
    int R = REPL > 64 ? 64 : REPL, stopped = 0;
    for (int r = 0; r < R; r++)
        for (int i = 0; i < n; i++) {
            xs[r][i] = -0.1 + 0.2 * rndu();
            ys[r][i] = -0.1 + 0.2 * rndu();
        }
    for (int k = 0; k < STEPS; k++) {
        double a = A0 - A0 * k / STEPS;
        for (int r = 0; r < R; r++) {
            u64 pos = 0;
            for (int i = 0; i < n; i++)
                if (xs[r][i] > 0) pos |= 1ULL << i;
            for (int i = 0; i < n; i++) {
                double field = -(2.0 * pc(A[i] & pos) - deg[i]);
                ys[r][i] += DT * (-a * xs[r][i] + c0 * field);
            }
            for (int i = 0; i < n; i++) {
                xs[r][i] += DT * A0 * ys[r][i];
                if (fabs(xs[r][i]) > 1.0) {
                    xs[r][i] = xs[r][i] > 0 ? 1.0 : -1.0;
                    ys[r][i] = 0.0;
                }
            }
        }
        if (k % 50 == 49 && cpu_ms() >= deadline) {
            stopped = 1;
            break;
        }
    }
    for (int r = 0; r < R; r++) {
        u64 pos = 0;
        for (int i = 0; i < n; i++)
            if (xs[r][i] > 0) pos |= 1ULL << i;
        offer_side(pos);
    }
    return stopped;
}

static u64 descent_side(void) {
    u64 side = 0;
    for (int i = 0; i < n; i++)
        if (rndu() < 0.5) side |= 1ULL << i;
    int perm[MAXN];
    for (int i = 0; i < n; i++) perm[i] = i;
    int improved = 1;
    while (improved) {
        improved = 0;
        shuffle(perm, n);
        for (int t = 0; t < n; t++) {
            int v = perm[t];
            u64 same = ((side >> v) & 1) ? (A[v] & side) : (A[v] & ~side);
            if (2 * pc(same) > deg[v]) {
                side ^= 1ULL << v;
                improved = 1;
            }
        }
    }
    return side;
}
static void descent_one(void) { offer_side(descent_side()); }

/* three-body mean-field annealing on the edge variables: p_e = sigmoid((1 - lam * sum_T p_f p_g) / temp) */
static double pe[MAXM];
static int tri_off[MAXM + 1], *tri_ff, *tri_gg;
static double hf[MAXM], gf[MAXM];
static void fem_grad(void) {
    /* free-energy machine style: fields h, p = sigmoid(h), gradient of F = -sum p + lam sum_T ppp - T S(p),
       normalised steps, temperature annealed geometrically; fields start near zero (random) */
    for (int i = 0; i < m; i++) { hf[i] = 0.2 * (rndu() - 0.5); pe[i] = 1.0 / (1.0 + exp(-hf[i])); }
    double t0 = 1.0, t1 = 0.01;
    for (int k = 0; k < FEMSTEPS; k++) {
        double temp = t0 * pow(t1 / t0, (double)k / (FEMSTEPS - 1)), norm = 0;
        for (int i = 0; i < m; i++) {
            double s = 0;
            for (int q = tri_off[i]; q < tri_off[i + 1]; q++) s += pe[tri_ff[q]] * pe[tri_gg[q]];
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
    if (FEMLR > 0) { fem_grad(); goto round; }
    for (int i = 0; i < m; i++) pe[i] = 0.3 + 0.4 * rndu();
    double t0 = 2.0, t1 = 0.02, eta = 0.5;
    for (int k = 0; k < FEMSTEPS; k++) {
        double temp = t0 * pow(t1 / t0, (double)k / (FEMSTEPS - 1));
        for (int i = 0; i < m; i++) {
            double s = 0;
            for (int q = tri_off[i]; q < tri_off[i + 1]; q++) s += pe[tri_ff[q]] * pe[tri_gg[q]];
            double h = (1.0 - FEMLAM * s) / temp;
            double target = h > 30 ? 1.0 : h < -30 ? 0.0 : 1.0 / (1.0 + exp(-h));
            pe[i] = (1 - eta) * pe[i] + eta * target;
        }
    }
round:;
    /* round: add in decreasing p, then fill */
    Sol S;
    s_clear(&S);
    for (int i = 0; i < m; i++) {
        cbuf[i] = i;
        key[i] = pe[i] + 1e-6 * rndu();
    }
    qsort(cbuf, m, sizeof(int), cmp_key);
    for (int i = 0; i < m; i++)
        if (s_free(&S, cbuf[i])) s_add(&S, cbuf[i]);
    offer_sol(&S);
}

/* ---------- phase 2 ---------- */
static Sol mem[POOLMAX], cur[POOLMAX];
static double temp_of[POOLMAX];

static int accept(int j, int newsize, int oldsize) {
    if (newsize >= oldsize) return 1;
    if (ACC == 0) return rndu() < PW;
    return rndu() < exp((newsize - oldsize) / temp_of[j]);
}

static void crossover(int k, double deadline) {
    int a = rndn(k), b = rndn(k - 1);
    if (b >= a) b++;
    Sol C;
    s_clear(&C);
    for (int i = 0; i < m; i++)
        if (cur[a].in[i] && cur[b].in[i]) s_add(&C, i);
    fill_all(&C);
    swaps(&C, deadline);
    offer_best(&C);
    st_cross++;
    int worst = 0;
    for (int j = 1; j < k; j++)
        if (cur[j].size < cur[worst].size) worst = j;
    if (C.size <= cur[worst].size) return;
    for (int j = 0; j < k; j++)
        if (cur[j].size == C.size && !memcmp(cur[j].in, C.in, m)) return;
    cur[worst] = C;
    mem[worst] = C;
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
    if (K < 1 || K > 32) return 2;
    long long seed;
    double budget;
    if (scanf("%d %d %lld %lf", &n, &m, &seed, &budget) != 4 || n < 1 || n > MAXN || m < 0 || m > MAXM) return 2;
    double start = cpu_ms(), deadline = start + budget;
    memset(eidm, -1, sizeof eidm);
    for (int i = 0; i < m; i++) {
        if (scanf("%d %d", &eu[i], &ev[i]) != 2) return 2;
        int u = eu[i], v = ev[i];
        if (u < 0 || v >= n || u >= v || eidm[u][v] >= 0) return 2;
        eidm[u][v] = eidm[v][u] = (short)i;
        A[u] |= 1ULL << v;
        A[v] |= 1ULL << u;
        inc[u][ninc[u]++] = i;
        inc[v][ninc[v]++] = i;
    }
    for (int i = 0; i < n; i++) deg[i] = pc(A[i]);
    rs[0] = (u64)seed * 0x9E3779B97F4A7C15ULL + 0x632BE59BD9B4E019ULL;
    rs[1] = rs[0] ^ 0xD1B54A32D192ED03ULL;
    for (int i = 0; i < 20; i++) rnd64();
    for (int i = 0; i < m; i++) tau[i] = 0.5;
    s_clear(&best);
    if (m > 0 && (WS & 4)) {
        int tot = 0;
        for (int i = 0; i < m; i++) tot += pc(A[eu[i]] & A[ev[i]]);
        tri_ff = malloc(sizeof(int) * (tot + 1));
        tri_gg = malloc(sizeof(int) * (tot + 1));
        int q = 0;
        for (int i = 0; i < m; i++) {
            tri_off[i] = q;
            u64 c = A[eu[i]] & A[ev[i]];
            while (c) {
                int w = ctz(c);
                c &= c - 1;
                tri_ff[q] = eidm[eu[i]][w];
                tri_gg[q] = eidm[ev[i]][w];
                q++;
            }
        }
        tri_off[m] = q;
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
            if (npool > 4 * K) {
                qsort(pool, npool, sizeof(Entry), cmp_pool);
                npool = K;
            }
            if (stopped || !(WS & 7)) break;
        }
        if (npool == 0) {      /* no warm-start component: random greedy fills */
            Sol S;
            s_clear(&S);
            fill_all(&S);
            offer_sol(&S);
        }
    }
    /* phase 2 */
    {
        qsort(pool, npool, sizeof(Entry), cmp_pool);
        int k = npool < K ? npool : K;
        for (int j = 0; j < k; j++) {
            mem[j] = pool[j].s;
            swaps(&mem[j], deadline);
            offer_best(&mem[j]);
            cur[j] = mem[j];
            temp_of[j] = k > 1 ? TMIN * pow(TMAX / TMIN, (double)j / (k - 1)) : TMIN;
        }
        long long it = 0, stall[POOLMAX] = {0};
        int j = 0;
        while (cpu_ms() < deadline) {
            Sol *S = &mem[j];
            for (int q = 0; q < KICKS; q++) kick(S);
            swaps(S, deadline);
            offer_best(S);
            if (S->size > cur[j].size) stall[j] = 0; else stall[j]++;
            if (accept(j, S->size, cur[j].size))
                cur[j] = *S;
            else
                *S = cur[j];
            if (RESTART > 0 && stall[j] >= RESTART) {      /* a fresh start from a new cut descent */
                complete_cut(descent_side(), S);
                swaps(S, deadline);
                offer_best(S);
                cur[j] = *S;
                stall[j] = 0;
                st_restarts++;
            }
            it++;
            st_iters++;
            if (ACC == 1 && k > 1 && it % XCHG == 0) {
                for (int a = 0; a + 1 < k; a++) {
                    double d = (cur[a + 1].size - cur[a].size) * (1.0 / temp_of[a] - 1.0 / temp_of[a + 1]);
                    if (d >= 0 || rndu() < exp(d)) {
                        Sol t = cur[a];
                        cur[a] = cur[a + 1];
                        cur[a + 1] = t;
                        mem[a] = cur[a];
                        mem[a + 1] = cur[a + 1];
                        st_xchg++;
                    }
                }
            }
            if (CROSS > 0 && k > 1 && it % CROSS == 0) crossover(k, deadline);
            j = (j + 1) % k;
        }
    }
out:
    printf("c starts %lld iters %lld swaps %lld cross %lld/%lld xchg %lld restarts %lld t_best_ms %.1f\n", st_starts,
           st_iters, st_swaps, st_cross_ok, st_cross, st_xchg, st_restarts, t_best - start);
    printf("v ");
    for (int i = 0; i < m; i++) putchar(best.in[i] ? '1' : '0');
    printf("\ns %d\n", best.size);
    return 0;
}
