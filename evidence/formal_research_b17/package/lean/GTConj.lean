import GTConcepts
set_option linter.unusedVariables false
namespace GTConj
/-- Generated conjecture `down_closed` (generated:template). -/
def down_closed : Prop := ∀ (S : GT.Edges) (T : GT.Edges) (h1 : T ⊆ S) (h2 : GT.TriangleFree S), GT.TriangleFree T
/-- Generated conjecture `union_closed` (generated:template). -/
def union_closed : Prop := ∀ (S : GT.Edges) (T : GT.Edges) (h1 : GT.TriangleFree S) (h2 : GT.TriangleFree T), GT.TriangleFree (S ∪ T)
def union_closed_negation : Prop := ¬ union_closed
/-- Generated conjecture `union_closed_simple` (generated:hypothesis-correction-of:union_closed). -/
def union_closed_simple : Prop := ∀ (S : GT.Edges) (T : GT.Edges) (hsS : GT.Simple S) (hsT : GT.Simple T) (h1 : GT.TriangleFree S) (h2 : GT.TriangleFree T), GT.TriangleFree (S ∪ T)
def union_closed_simple_negation : Prop := ¬ union_closed_simple
/-- Generated conjecture `inter_closed` (generated:template). -/
def inter_closed : Prop := ∀ (S : GT.Edges) (T : GT.Edges) (h1 : GT.TriangleFree S), GT.TriangleFree (S ∩ T)
/-- Generated conjecture `insert_closed` (generated:template). -/
def insert_closed : Prop := ∀ (S : GT.Edges) (e : ℕ × ℕ) (h1 : GT.TriangleFree S), GT.TriangleFree (insert e S)
def insert_closed_negation : Prop := ¬ insert_closed
/-- Generated conjecture `insert_closed_simple` (generated:hypothesis-correction-of:insert_closed). -/
def insert_closed_simple : Prop := ∀ (S : GT.Edges) (e : ℕ × ℕ) (hsS : GT.Simple S) (hse : e.1 < e.2) (h1 : GT.TriangleFree S), GT.TriangleFree (insert e S)
def insert_closed_simple_negation : Prop := ¬ insert_closed_simple
/-- Generated conjecture `bound_card` (generated:template). -/
def bound_card : Prop := ∀ (A : GT.Edges), GT.TFBound A A.card
/-- Generated conjecture `bound_union` (generated:template). -/
def bound_union : Prop := ∀ (A : GT.Edges) (B : GT.Edges) (a : ℕ) (b : ℕ) (h1 : GT.TFBound A a) (h2 : GT.TFBound B b), GT.TFBound (A ∪ B) (a + b)
/-- Generated conjecture `bound_mono` (generated:template). -/
def bound_mono : Prop := ∀ (A : GT.Edges) (B : GT.Edges) (a : ℕ) (b : ℕ) (h1 : GT.TFBound B a) (h2 : A ⊆ B) (h3 : a ≤ b), GT.TFBound A b
/-- Generated conjecture `bound_insert` (generated:template). -/
def bound_insert : Prop := ∀ (A : GT.Edges) (a : ℕ) (e : ℕ × ℕ) (h1 : GT.TFBound A a), GT.TFBound (insert e A) a
def bound_insert_negation : Prop := ¬ bound_insert
/-- Generated conjecture `bound_le_card` (generated:template). -/
def bound_le_card : Prop := ∀ (A : GT.Edges) (a : ℕ) (h1 : GT.TFBound A a), a ≤ A.card
def bound_le_card_negation : Prop := ¬ bound_le_card
/-- Generated conjecture `bound_zero_empty` (generated:template). -/
def bound_zero_empty : Prop := ∀ (A : GT.Edges) (h1 : GT.TFBound A 0), A = ∅
def bound_zero_empty_negation : Prop := ¬ bound_zero_empty
/-- Generated conjecture `bound_zero_empty_simple` (generated:hypothesis-correction-of:bound_zero_empty). -/
def bound_zero_empty_simple : Prop := ∀ (A : GT.Edges) (hsA : GT.Simple A) (h1 : GT.TFBound A 0), A = ∅
/-- Generated conjecture `mantel` (generated:template). -/
def mantel : Prop := ∀ (A : GT.Edges) (n : ℕ) (h1 : ∀ e ∈ A, e.1 < e.2 ∧ e.2 < n), GT.TFBound A (n * n / 4)
/-- Generated conjecture `gadget_Gad3e3_bound` (generated:gadget-search). -/
def gadget_Gad3e3_bound : Prop := GT.TFBound (GT.Gad3e3 0 1 2) 2
/-- Generated conjecture `gadget_Gad3e3_tight` (generated:gadget-search). -/
def gadget_Gad3e3_tight : Prop := ¬ GT.TFBound (GT.Gad3e3 0 1 2) 1
/-- Generated conjecture `gadget_Gad4e6_bound` (generated:gadget-search). -/
def gadget_Gad4e6_bound : Prop := GT.TFBound (GT.Gad4e6 0 1 2 3) 4
/-- Generated conjecture `gadget_Gad4e6_tight` (generated:gadget-search). -/
def gadget_Gad4e6_tight : Prop := ¬ GT.TFBound (GT.Gad4e6 0 1 2 3) 3
end GTConj
