import Init
set_option maxRecDepth 100000
set_option maxHeartbeats 10000000
namespace GenesisFinite
def witness : List (Nat × Nat) := [(0, 1), (0, 2), (0, 3), (1, 2)]
def adj (u v : Nat) : Bool := witness.contains (min u v, max u v)
def vertices : List Nat := List.range 4
def simple : Bool := witness.all (fun e => decide (e.1 < e.2) && decide (e.2 < 4))
def triangleFree : Bool := vertices.all (fun a => vertices.all (fun b => vertices.all (fun c =>
  !(adj a b && adj b c && adj c a))))
def c4Free : Bool := vertices.all (fun a => vertices.all (fun b => vertices.all (fun c => vertices.all (fun d =>
  !((a != b && a != c && a != d && b != c && b != d && c != d) &&
    adj a b && adj b c && adj c d && adj d a)))))
theorem simple_checked : simple = true := by decide
theorem witness_checked : c4Free = true := by decide
theorem size_checked : witness.length = 4 := by decide
#print axioms simple_checked
#print axioms witness_checked
#print axioms size_checked
end GenesisFinite
