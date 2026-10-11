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
import GTP11
namespace GTP12
theorem proof : GTConj.bound_zero_empty_negation := by
  unfold GTConj.bound_zero_empty_negation GTConj.bound_zero_empty
  intro h
  exact absurd (h (({(2, 2)} : GT.Edges)) (by decide +kernel)) (by decide +kernel)
end GTP12
