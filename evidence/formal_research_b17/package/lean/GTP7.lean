import GTDefs
import GTConcepts
import GTConj
import GTP1
import GTP2
import GTP3
import GTP4
import GTP5
import GTP6
namespace GTP7
theorem proof : GTConj.bound_card := by
  unfold GTConj.bound_card
  intros
  try unfold GT.TFBound at *
  try unfold GT.TriangleFree at *
  solve_by_elim [Finset.card_le_card, Finset.Subset.trans]
end GTP7
