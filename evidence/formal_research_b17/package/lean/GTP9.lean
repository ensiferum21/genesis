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
namespace GTP9
theorem proof : GTConj.bound_mono := by
  unfold GTConj.bound_mono
  intro A B a b h1 h2 h3
  try unfold GT.TFBound at *
  try unfold GT.TriangleFree at *
  intro S hS hT
  have := h1 S (by solve_by_elim [Finset.Subset.trans]) hT
  omega
end GTP9
