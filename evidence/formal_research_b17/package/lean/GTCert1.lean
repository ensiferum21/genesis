import GTConcepts
import GTTask1
import GTP1
import GTP10
import GTP11
import GTP12
import GTP13
import GTP14
import GTP15
import GTP16
import GTP2
import GTP3
import GTP4
import GTP5
import GTP6
import GTP7
import GTP8
import GTP9
namespace GTCert1
def rest : GT.Edges := {(0, 9), (0, 13), (0, 14), (0, 18), (0, 19), (1, 3), (1, 18), (1, 19), (3, 13), (3, 16), (3, 20), (4, 20), (5, 6), (5, 20), (5, 21), (6, 8), (6, 17), (7, 15), (7, 20), (8, 13), (8, 15), (8, 16), (8, 20), (9, 10), (9, 12), (10, 17), (10, 20), (11, 18), (11, 19), (11, 20), (14, 21), (15, 18), (16, 21)}
theorem proof : GTTask1.stmt := by
  unfold GTTask1.stmt
  have h0 : GT.TFBound (GT.Gad4e6 0 1 6 10) 4 := by decide
  have h1 : GT.TFBound (GT.Gad4e6 0 2 16 20) 4 := by decide
  have h2 : GT.TFBound (GT.Gad4e6 0 5 7 11) 4 := by decide
  have h3 : GT.TFBound (GT.Gad4e6 1 4 11 21) 4 := by decide
  have h4 : GT.TFBound (GT.Gad4e6 4 6 9 15) 4 := by decide
  have h5 : GT.TFBound (GT.Gad3e3 2 12 14) 2 := by decide
  have h6 : GT.TFBound (GT.Gad3e3 2 17 18) 2 := by decide
  have h7 : GT.TFBound (GT.Gad3e3 3 6 21) 2 := by decide
  have h8 : GT.TFBound (GT.Gad3e3 3 7 14) 2 := by decide
  have h9 : GT.TFBound (GT.Gad3e3 4 14 17) 2 := by decide
  have h10 : GT.TFBound (GT.Gad3e3 7 12 18) 2 := by decide
  have h11 : GT.TFBound (GT.Gad3e3 7 16 17) 2 := by decide
  have h12 : GT.TFBound (GT.Gad3e3 10 11 16) 2 := by decide
  have h13 : GT.TFBound (GT.Gad3e3 10 13 21) 2 := by decide
  have hr : GT.TFBound rest rest.card := GTP7.proof rest
  exact GTP9.proof _ _ _ _ (GTP8.proof _ _ _ _ h0 (GTP8.proof _ _ _ _ h1 (GTP8.proof _ _ _ _ h2 (GTP8.proof _ _ _ _ h3 (GTP8.proof _ _ _ _ h4 (GTP8.proof _ _ _ _ h5 (GTP8.proof _ _ _ _ h6 (GTP8.proof _ _ _ _ h7 (GTP8.proof _ _ _ _ h8 (GTP8.proof _ _ _ _ h9 (GTP8.proof _ _ _ _ h10 (GTP8.proof _ _ _ _ h11 (GTP8.proof _ _ _ _ h12 (GTP8.proof _ _ _ _ h13 hr)))))))))))))) (by decide +kernel) (by decide +kernel)
end GTCert1
