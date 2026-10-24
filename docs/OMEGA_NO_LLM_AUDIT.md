# Genesis Ω: no-LLM audit (master implementation contract §0, §16.10)

**Rule.** No LLM inference, LLM API, hosted model call, pretrained language-model embedding, LLM-derived planning
agent, hidden fallback or human-in-the-loop idea generation is part of the Genesis runtime or of its measured
autonomous experiments. The external coding agent that builds the repository (the builder) is not a runtime
component. What it writes is code, reviewed by tests; Genesis never calls it.

**Automated enforcement: `tests_genesis/test_no_llm.py`** (commit profile, must pass):
1. **Static import scan.** No `.py` file under `src`, `scripts`, `custody_reference`, `legacy_batch42` or any test
   directory imports a banned module. This includes `import_module("…")` calls with literal names. The banned list
   covers LLM clients, model hubs, tokenizers, agent frameworks and quantised-model runtimes (in the test).
2. **Hosts and packages.** No runtime file or configuration names an LLM API host. No `requirements.lock` or
   `pyproject.toml` line names a banned package.
3. **Dynamic check.** Importing the research packages (the scientist, the acquisition language, the causal adapter,
   the feedback contract, the inventor, the research loop, the knowledge map, the research ecology, the store, the
   evidence kernel) loads no banned module.
4. **Identity.** The research loop commits as itself (`autonomy/loop.IDENTITY`), never as an assistant.
5. **Negative control.** A planted file with banned imports and an API host is detected. A detector that cannot fire
   proves nothing.

**Findings (24 Oct 2026).**

| Check | Result |
|---|---|
| Static imports | none found |
| Hosts and packages | none found |
| Dynamic imports | none loaded |
| Identity | **one defect, fixed**: `autonomy/loop.preregister` committed as "Claude" with assistant trailers. It now commits as "Genesis research loop"; an operator may pass attribution trailers |

**Allowed, if ever used.** Conventional neural networks, graph models, reinforcement learning, symbolic regression,
Bayesian models and evolutionary methods trained by Genesis under auditable conditions. Each must document its
training data, architecture, compute, provenance, inference path and an ablation. None is used today: the runtime's
learning is evolutionary search, Bayesian updating, calibration by simulation and counting.
