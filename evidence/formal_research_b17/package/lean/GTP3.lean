import GTDefs
import GTConcepts
import GTConj
import GTP1
import GTP2
namespace GTP3
theorem proof : GTConj.union_closed_simple_negation := by
  unfold GTConj.union_closed_simple_negation GTConj.union_closed_simple
  intro h
  exact absurd (h (({(0, 2), (1, 2)} : GT.Edges)) (({(0, 1)} : GT.Edges)) (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide +kernel)) (by decide +kernel)
end GTP3
