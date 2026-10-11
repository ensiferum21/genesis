"""The Lean statement domain under the W05 DomainAdapter interface.

A task is a trusted context (Genesis-generated modules: definitions, concepts) and
one statement, a Lean `Prop`. A witness is an untrusted proof module. It is valid
exactly when `checker.accept` binds it to the statement in fresh sandboxes against
the audited workspace, with only the allowed axioms and a leanchecker replay.

What the domain cannot do is explicit:
  * exact_reference is UNSUPPORTED: a statement has no optimum to certify;
  * the exposure identity is the statement text after whitespace normalisation, plus
    its context. That is not semantic equivalence, a residual risk disclosed in the
    contract.
The domain is not in `kernel.receipts.DOMAINS`, so no sealed receipt can name it until
a later batch registers a scored contract for it (fail closed).
"""
import re
from typing import Literal

from pydantic import Field, model_validator

from ..common import digest
from ..domains import INTERFACE, PURPOSES, DomainAdapter, Unsupported
from ..models import StrictModel
from . import checker as C

DOMAIN = 'lean_statement_v1'
CONTRACT = {'objective': 'a kernel-checked proof of a fixed Lean statement over a trusted context',
            'witness': 'an untrusted Lean proof module defining `proof : <Spec>.stmt`', 'score': '1 if accepted, else 0',
            'checker': 'genesis.formal_research.checker.accept (sandboxed, axiom audit, leanchecker)', 'version': 1,
            'exposure': 'whitespace-normalised statement text and context hashes (not semantic equivalence)',
            'sealed_receipts': 'not registered in kernel.receipts.DOMAINS'}


class ContextModule(StrictModel):
    name: str = Field(pattern=r'^[A-Z][A-Za-z0-9]{0,63}$')
    source: str = Field(min_length=1, max_length=200000)


class LeanStatementTask(StrictModel):
    task_id: str = Field(min_length=1, max_length=128)
    domain: Literal['lean_statement_v1'] = DOMAIN
    context: tuple[ContextModule, ...]
    statement: str = Field(min_length=1, max_length=20000)
    family: str = Field(min_length=1, max_length=128)
    split: Literal['DEV', 'SELECT', 'CONFIRM', 'FUTURE'] = 'DEV'

    @model_validator(mode='after')
    def labels(self):
        if not (self.task_id.isprintable() and self.family.isprintable()):
            raise ValueError('task_id and family must be printable single-line labels')
        if len({m.name for m in self.context}) != len(self.context) or 'GTStmt' in {m.name for m in self.context}:
            raise ValueError('context module names must be distinct and must not be GTStmt')
        return self


class CandidateStatement(StrictModel):
    """What a prover may see: the context and the statement. No id, family, split."""
    domain: Literal['lean_statement_v1'] = DOMAIN
    context: tuple[ContextModule, ...]
    statement: str


SPEC = 'GTStmt'


def spec_module(task):
    imports = ''.join(f'import {m.name}\n' for m in task.context)
    return f'{imports}namespace {SPEC}\ndef stmt : Prop := {task.statement}\nend {SPEC}\n'


class LeanStatementAdapter(DomainAdapter):
    name = DOMAIN

    def contract(self):
        return {'schema': 'genesis-domain-contract-v1', 'domain': self.name, **CONTRACT}

    def parse(self, raw):
        if isinstance(raw, LeanStatementTask):
            return raw
        if not isinstance(raw, dict) or raw.get('domain') != self.name:
            return Unsupported(f'task domain {raw.get("domain") if isinstance(raw, dict) else None!r} is not {self.name}')
        try:
            from ..common import canonical
            return LeanStatementTask.model_validate_json(canonical(raw))
        except Exception as exc:
            return Unsupported(f'malformed task: {type(exc).__name__}')

    def supports(self, task, purpose):
        if purpose not in PURPOSES:
            return Unsupported(f'unknown purpose {purpose!r}')
        if not isinstance(task, LeanStatementTask):
            return Unsupported('not a task of this domain')
        if purpose == 'exact_reference':
            return Unsupported('a statement has no exact reference optimum')
        for pattern in C.FORBIDDEN:
            if re.search(pattern, task.statement):
                return Unsupported('the statement contains a forbidden construct')
        return None

    def exposure_identity(self, task):
        return {'canonical': digest({'statement': ' '.join(task.statement.split()),
                                     'context': [digest(m.source) for m in task.context]}),
                'method': 'normalised-text (not semantic equivalence)'}

    def candidate_view(self, task):
        return CandidateStatement(context=task.context, statement=task.statement)

    def validate(self, task, witness):
        unsupported = self.supports(task, 'certificate')
        if unsupported:
            return unsupported.record()
        if not isinstance(witness, str):
            return {'status': 'INVALID', 'reason': 'the witness must be the source of a proof module'}
        modules = [{'name': m.name, 'source': m.source, 'trusted': True} for m in task.context]
        modules += [{'name': SPEC, 'source': spec_module(task), 'trusted': True},
                    {'name': 'GTWitness', 'source': witness, 'trusted': False}]
        try:
            r = C.accept(modules, [{'spec': f'{SPEC}.stmt', 'proof': 'GTWitness.proof'}])
        except C.ChainError as exc:
            return {'status': 'INVALID', 'reason': str(exc)}
        b = r['bindings'][0]
        if b['status'] == 'CHECKED':
            return {'status': 'VALID', 'value': 1, 'axioms': b.get('axioms'), 'receipt_sha256': digest(r)}
        if b['status'] in ('CHECKER_ERROR', 'TIMEOUT'):
            return {'status': b['status'], 'reason': r.get('reason'), 'outcome_class': b['outcome_class']}
        return {'status': 'INVALID', 'reason': b['status'], 'outcome_class': b['outcome_class']}

    def score(self, task, witness):
        v = self.validate(task, witness)
        return v['value'] if v['status'] == 'VALID' else None

    def reference(self, task, *, evidence=None, seconds=600):
        return Unsupported('a statement has no exact reference optimum')

    def certificate_obligations(self, claim, value):
        return [{'obligation': 'kernel_checked_proof',
                 'evidence': 'checker.accept receipt: statement binding, axiom audit, leanchecker replay'}]

    def cost(self, receipt):
        return {'status': receipt.get('status'), 'wall_ns': receipt.get('wall_ns'), 'cpu_ns': receipt.get('cpu_ns'),
                'peak_rss_bytes': receipt.get('peak_memory_bytes'), 'queries': None, 'category': 'proof-checking'}

    def families(self):
        return {'theory-template': {'params': {'theory': ['triangle-obstruction']},
                                    'note': 'screened (not falsified) conjectures of a theory generator'}}

    def generate(self, seed, count, split, family, params, excluded=()):
        """Tasks from a theory generator's screened conjectures (never from confirmation results)."""
        if family != 'theory-template' or params.get('theory') != 'triangle-obstruction':
            raise ValueError(f'unknown family {family!r} / params {params!r}')
        from . import theory_package as TP, triangle_theory as T
        gen = TP.generate(seed)
        context = (ContextModule(name=T.DEFS_MODULE, source=T.DEFS_SOURCE),
                   ContextModule(name=T.CONCEPTS_MODULE, source=T.concepts_source(gen['catalog'])))
        seen, out = set(excluded), []
        for c in gen['conjectures']:
            if c['counterexample'] is not None or len(out) >= count:
                continue
            t = LeanStatementTask(task_id=f'{split.lower()}-{c["id"]}', context=context, statement=c['lean'],
                                  family=family, split=split)
            key = self.exposure_identity(t)['canonical']
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        return out, seen, {'generator': 'theory_package.generate', 'seed': seed}

    def replay(self, record):
        task = self.parse(record.get('task'))
        if isinstance(task, Unsupported):
            return task.record()
        checked = self.validate(task, record.get('witness'))
        if checked['status'] != 'VALID':
            return checked
        return {'status': 'REPLAYED', 'value': 1}


ADAPTER = LeanStatementAdapter()
FORMAL_ADAPTERS = {DOMAIN: ADAPTER}

__all__ = ['LeanStatementAdapter', 'LeanStatementTask', 'CandidateStatement', 'ADAPTER', 'FORMAL_ADAPTERS',
           'spec_module', 'INTERFACE']
