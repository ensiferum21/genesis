/* Test builds only (never installed, never pinned; `scripts/b20r153_build_mcx3.py`, `build_test`): a counting
   clock in place of the CPU clock, so that a run is a function of its input, and a trace of the run: at every call
   of exp (once per attractor of breakout local search, once per replica-exchange attempt) the clock reading and the
   argument are folded into a hash, printed on stderr at exit with the number of calls and of clock readings. Two
   builds whose traces agree made the same moves with the same clock readings at those points. */
#include <time.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
static unsigned long genesis_ticks, genesis_calls;
static uint64_t genesis_hash = 1469598103934665603ULL;
static clock_t genesis_tick_clock(void) { return (clock_t)(++genesis_ticks); }
static void genesis_fold(uint64_t x) { for (int i = 0; i < 8; i++) { genesis_hash ^= (x >> (8 * i)) & 255; genesis_hash *= 1099511628211ULL; } }
static double genesis_exp(double x) { uint64_t b; memcpy(&b, &x, 8); genesis_fold(genesis_ticks); genesis_fold(b); genesis_calls++; return exp(x); }
__attribute__((destructor)) static void genesis_report(void) { fprintf(stderr, "trace %016llx %lu %lu\n", (unsigned long long)genesis_hash, genesis_calls, genesis_ticks); }
#define clock genesis_tick_clock
#define exp genesis_exp
