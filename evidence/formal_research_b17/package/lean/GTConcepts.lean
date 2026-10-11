import GTDefs

namespace GT

/-- Generated bound concept: `k` bounds every triangle-free edge set inside `H`. -/
def TFBound (H : Edges) (k : ℕ) : Prop := ∀ S ⊆ H, TriangleFree S → S.card ≤ k

instance (H : Edges) (k : ℕ) : Decidable (TFBound H k) := by
  unfold TFBound; infer_instance

/-- Generated normal form: every pair is listed with u < v. -/
def Simple (S : Edges) : Prop := ∀ e ∈ S, e.1 < e.2

instance (S : Edges) : Decidable (Simple S) := by
  unfold Simple; infer_instance

/-- Generated gadget: 3 vertices, 3 edges, triangle-free bound 2. -/
def Gad3e3 (v0 v1 v2 : ℕ) : Edges := {(v0, v1), (v0, v2), (v1, v2)}

/-- Generated gadget: 4 vertices, 6 edges, triangle-free bound 4. -/
def Gad4e6 (v0 v1 v2 v3 : ℕ) : Edges := {(v0, v1), (v0, v2), (v0, v3), (v1, v2), (v1, v3), (v2, v3)}

end GT
