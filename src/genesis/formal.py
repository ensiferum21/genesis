"""Generate finite Lean obligations; fail closed without a pinned checker.

Source generation is NOT theorem verification. Existing gap_engine Lean custody
adapters remain available for externally pinned theorem-canary workflows.
"""
from pathlib import Path
import shutil
from .common import bytes_hash,canonical
from .graphs import check_witness


def export_witness(task,edges,destination):
    checked=check_witness(task,edges)
    literal='['+', '.join(f'({u}, {v})' for u,v in checked['selected'])+']'
    # This is generated exclusively from validated integers, with no untrusted
    # tactic text, commands, imports, names or arbitrary source interpolation.
    lines=['import Init','set_option maxRecDepth 100000','set_option maxHeartbeats 10000000',
      'namespace GenesisFinite',
      f'def witness : List (Nat × Nat) := {literal}',
      'def adj (u v : Nat) : Bool := witness.contains (min u v, max u v)',
      f'def vertices : List Nat := List.range {task.n}',
      'def simple : Bool := witness.all (fun e => decide (e.1 < e.2) && decide (e.2 < '+str(task.n)+'))',
      'def triangleFree : Bool := vertices.all (fun a => vertices.all (fun b => vertices.all (fun c =>',
      '  !(adj a b && adj b c && adj c a))))',
      'def c4Free : Bool := vertices.all (fun a => vertices.all (fun b => vertices.all (fun c => vertices.all (fun d =>',
      '  !((a != b && a != c && a != d && b != c && b != d && c != d) &&',
      '    adj a b && adj b c && adj c d && adj d a)))))',
      'theorem simple_checked : simple = true := by decide',
      f"theorem witness_checked : {'c4Free' if task.domain=='c4_host_v2' else 'triangleFree'} = true := by decide",
      f"theorem size_checked : witness.length = {checked['value']} := by decide",
      '#print axioms simple_checked','#print axioms witness_checked','#print axioms size_checked',
      'end GenesisFinite','']
    source='\n'.join(lines).encode();root=Path(destination);root.mkdir(parents=True,exist_ok=False)
    (root/'Main.lean').write_bytes(source)
    obligation={'schema':'genesis-finite-lean-obligation-v1','source_sha256':bytes_hash(source),
                'task':task.model_dump(mode='json'),'selected':checked['selected'],
                'status':'SOURCE_GENERATED_NOT_CHECKED','formal_proof':False,
                'scope':'finite witness predicate and cardinality; no universal optimum theorem',
                'requires':['externally pinned Lean executable and full library environment',
                            'positive and negative canaries','theorem identity and axiom replay',
                            'review of Boolean predicate to intended graph semantics'],
                'documentation':['https://lean-lang.org/doc/reference/latest/ValidatingProofs/',
                                 'https://lean-lang.org/doc/reference/latest/Axioms/']}
    (root/'obligation.json').write_bytes(canonical(obligation))
    return obligation


def doctor():
    lean=shutil.which('lean');docker=shutil.which('docker')
    return {'lean_executable':lean,'docker_executable':docker,
            'formal_verification':'BLOCKED_NO_LEAN' if not lean else 'REQUIRES_EXTERNAL_PINS_AND_REPLAY',
            'arbitrary_code_execution':'BLOCKED_NO_DOCKER' if not docker else 'REQUIRES_PINNED_IMAGE_AND_ESCAPE_TESTS',
            'data_only_graph_dsl':'AVAILABLE','independent_custody':'EXTERNAL_OPERATOR_REQUIRED',
            'formal_claim_allowed':False,'scientific_promotion_allowed':False}
