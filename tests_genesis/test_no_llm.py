"""Genesis Ω master contract §0, §16 item 10: no LLM in the Genesis runtime or its measured experiments.

Enforced statically and dynamically:
  * no Python file of the runtime, its scripts or its tests imports an LLM client, model library or tokenizer;
  * no runtime file, configuration or lock names an LLM API host or package;
  * importing the research packages loads none of those modules;
  * the research loop's own commits carry the runtime's identity, not an assistant's.
A failure here is a contract violation to be fixed, never silenced (docs/OMEGA_NO_LLM_AUDIT.md).
"""
import ast
import importlib
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

BANNED_MODULES = {
    'openai', 'anthropic', 'langchain', 'langchain_core', 'langchain_community', 'llama_index', 'llama_cpp', 'vllm',
    'transformers', 'sentence_transformers', 'huggingface_hub', 'tiktoken', 'tokenizers', 'cohere', 'mistralai',
    'ollama', 'google.generativeai', 'google.genai', 'vertexai', 'groq', 'together', 'replicate', 'litellm',
    'guidance', 'dspy', 'instructor', 'autogen', 'crewai', 'semantic_kernel', 'gpt4all', 'ctransformers', 'peft',
    'bitsandbytes', 'xformers', 'mlx_lm', 'exllamav2', 'auto_gptq', 'optimum'}
BANNED_HOSTS = ('api.openai.com', 'api.anthropic.com', 'generativelanguage.googleapis.com', 'aiplatform.googleapis.com',
                'api.cohere.ai', 'api.cohere.com', 'api.mistral.ai', 'api.groq.com', 'api.together.xyz',
                'api.replicate.com', 'huggingface.co', 'openrouter.ai', 'api.deepseek.com', 'bedrock-runtime')
CODE_DIRS = ('src', 'scripts', 'custody_reference', 'legacy_batch42', 'tests', 'tests_genesis', 'tests_sandbox',
             'tests_formal', 'tests_certificates')
CONFIG_GLOBS = ('configs/**/*', 'pyproject.toml', 'requirements.lock', 'environment/**/*', 'deployment/**/*')
RUNTIME_PACKAGES = ('genesis.science.design', 'genesis.science.acquire', 'genesis.causal.active3',
                    'genesis.autonomy.feedback', 'genesis.autonomy.selfimprove', 'genesis.autonomy.loop',
                    'genesis.autonomy.kmap', 'genesis.research', 'genesis.store', 'genesis.kernel.evidence')


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
        elif isinstance(node, ast.Call) and getattr(node.func, 'attr', getattr(node.func, 'id', None)) in (
                'import_module', '__import__') and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            out.add(node.args[0].value)
    return out


def banned(name):
    parts = name.split('.')
    return any('.'.join(parts[:k]) in BANNED_MODULES for k in range(1, len(parts) + 1))


class NoLLM(unittest.TestCase):
    def test_no_file_imports_an_llm_library(self):
        bad = []
        for d in CODE_DIRS:
            for p in (ROOT / d).rglob('*.py'):
                if '__pycache__' in p.parts:
                    continue
                bad += [f'{p.relative_to(ROOT)}: {m}' for m in sorted(imported_modules(p)) if banned(m)]
        self.assertEqual(bad, [])

    def test_no_runtime_file_or_config_names_an_llm_host_or_package(self):
        bad = []
        files = [p for d in ('src', 'scripts') for p in (ROOT / d).rglob('*.py') if '__pycache__' not in p.parts]
        for g in CONFIG_GLOBS:
            files += [p for p in ROOT.glob(g) if p.is_file() and p.stat().st_size < 5_000_000]
        pkg = re.compile(r'^\s*(' + '|'.join(re.escape(m.split('.')[0]) for m in BANNED_MODULES) + r')\s*[=<>~!]',
                         re.I | re.M)
        for p in files:
            try:
                text = p.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            bad += [f'{p.relative_to(ROOT)}: {h}' for h in BANNED_HOSTS if h in text]
            if p.name in ('requirements.lock', 'pyproject.toml'):
                bad += [f'{p.relative_to(ROOT)}: {m.group(1)}' for m in pkg.finditer(text)]
        self.assertEqual(bad, [])

    def test_research_packages_load_no_llm_module(self):
        for name in RUNTIME_PACKAGES:
            importlib.import_module(name)
        loaded = [m for m in sys.modules if banned(m)]
        self.assertEqual(loaded, [])

    def test_the_research_loop_commits_as_itself(self):
        text = (ROOT / 'src' / 'genesis' / 'autonomy' / 'loop.py').read_text()
        self.assertNotIn('anthropic.com', text)
        self.assertNotIn('user.name=Claude', text)

    def test_the_detector_detects(self):
        # negative control: the scanner must flag a planted import and host
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.py'
            p.write_text('import openai\nfrom transformers import AutoModel\nimportlib.import_module("anthropic")\n'
                         'URL = "https://api.openai.com/v1"\n')
            self.assertEqual(sorted(m for m in imported_modules(p) if banned(m)), ['anthropic', 'openai',
                                                                                  'transformers'])
            self.assertTrue(any(h in p.read_text() for h in BANNED_HOSTS))
        self.assertFalse(banned('numpy'))
        self.assertTrue(banned('google.generativeai.types'))


if __name__ == '__main__':
    unittest.main()
