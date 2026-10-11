import GTDefs
import GTConcepts
import GTConj
import GTP1
import GTP2
import GTP3
import GTP4
import GTP5
import GTP6
import GTP7
import GTP8
import GTP9
namespace GTP10
theorem proof : GTConj.bound_insert_negation := by
  unfold GTConj.bound_insert_negation GTConj.bound_insert
  intro h
  exact absurd (h ((∅ : GT.Edges)) (0) (((1, 2) : ℕ × ℕ)) (by decide +kernel)) (by decide +kernel)
end GTP10
