import GTDefs
import GTConcepts
import GTConj
namespace GTP1
theorem proof : GTConj.down_closed := by
  unfold GTConj.down_closed
  intro S T h1 h2
  try unfold GT.TFBound at *
  try unfold GT.TriangleFree at *
  intros
  apply h2 <;> solve_by_elim
end GTP1
