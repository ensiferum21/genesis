import GTDefs
import GTConcepts
import GTConj
import GTP1
import GTP2
import GTP3
import GTP4
namespace GTP5
theorem proof : GTConj.insert_closed_negation := by
  unfold GTConj.insert_closed_negation GTConj.insert_closed
  intro h
  exact absurd (h ((∅ : GT.Edges)) (((1, 1) : ℕ × ℕ)) (by decide +kernel)) (by decide +kernel)
end GTP5
