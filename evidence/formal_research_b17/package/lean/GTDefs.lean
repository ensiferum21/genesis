import Mathlib.Data.Finset.Powerset

namespace GT

/-- Edge sets: ordered pairs (u, v), read as the edge {u, v}. Hosts list each edge once, with u < v. -/
abbrev Edges := Finset (ℕ × ℕ)

/-- No three edges (a, b), (b, c), (a, c). -/
def TriangleFree (S : Edges) : Prop :=
  ∀ e ∈ S, ∀ f ∈ S, ∀ g ∈ S, ¬ (e.1 = g.1 ∧ e.2 = f.1 ∧ f.2 = g.2)

instance (S : Edges) : Decidable (TriangleFree S) := by
  unfold TriangleFree; infer_instance

end GT
