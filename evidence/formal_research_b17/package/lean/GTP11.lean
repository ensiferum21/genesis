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
import GTP10
namespace GTP11
theorem proof : GTConj.bound_le_card_negation := by
  unfold GTConj.bound_le_card_negation GTConj.bound_le_card
  intro h
  exact absurd (h ((∅ : GT.Edges)) (1) (by decide +kernel)) (by decide +kernel)
end GTP11
