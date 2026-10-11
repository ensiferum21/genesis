import GTDefs
import GTConcepts
import GTConj
import GTP1
import GTP2
import GTP3
import GTP4
import GTP5
namespace GTP6
theorem proof : GTConj.insert_closed_simple_negation := by
  unfold GTConj.insert_closed_simple_negation GTConj.insert_closed_simple
  intro h
  exact absurd (h (({(0, 1), (1, 2)} : GT.Edges)) (((0, 2) : ℕ × ℕ)) (by decide +kernel) (by decide +kernel) (by decide +kernel)) (by decide +kernel)
end GTP6
