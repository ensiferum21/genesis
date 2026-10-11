import GTDefs
import GTConcepts
import GTConj
import GTP1
namespace GTP2
theorem proof : GTConj.union_closed_negation := by
  unfold GTConj.union_closed_negation GTConj.union_closed
  intro h
  exact absurd (h (({(2, 0), (2, 1)} : GT.Edges)) (({(0, 1)} : GT.Edges)) (by decide +kernel) (by decide +kernel)) (by decide +kernel)
end GTP2
