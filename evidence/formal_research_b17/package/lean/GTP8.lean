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
namespace GTP8
theorem proof : GTConj.bound_union := by
  unfold GTConj.bound_union
  intro A B a b h1 h2
  try unfold GT.TFBound at *
  try unfold GT.TriangleFree at *
  intro S hS hT
  have h1 := h1 (S ∩ A) Finset.inter_subset_right (GTP1.proof _ _ Finset.inter_subset_left hT)
  have h2 := h2 (S ∩ B) Finset.inter_subset_right (GTP1.proof _ _ Finset.inter_subset_left hT)
  have h3 : S ⊆ S ∩ A ∪ S ∩ B := by
    intro x hx; have := hS hx; simp only [Finset.mem_union, Finset.mem_inter] at this ⊢; tauto
  have h4 := (Finset.card_le_card h3).trans (Finset.card_union_le _ _)
  omega
end GTP8
