import GTDefs
import GTConcepts
import GTConj
import GTP1
import GTP2
import GTP3
namespace GTP4
theorem proof : GTConj.inter_closed := by
  unfold GTConj.inter_closed
  intro S T h1
  try unfold GT.TFBound at *
  try unfold GT.TriangleFree at *
  aesop
end GTP4
