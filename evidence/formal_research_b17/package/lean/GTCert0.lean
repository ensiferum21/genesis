import GTConcepts
import GTTask0
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
namespace GTCert0
def rest : GT.Edges := {(0, 9), (1, 17), (1, 21), (2, 3), (2, 8), (2, 17), (3, 7), (3, 12), (4, 21), (5, 7), (5, 10), (5, 13), (6, 10), (6, 15), (6, 20), (7, 16), (7, 21), (8, 13), (8, 15), (8, 16), (9, 13), (9, 17), (10, 18), (11, 13), (11, 16), (12, 13), (12, 14), (12, 16), (12, 20), (16, 17), (17, 20), (18, 20)}
theorem proof : GTTask0.stmt := by
  unfold GTTask0.stmt
  have h0 : GT.TFBound (GT.Gad4e6 0 1 12 18) 4 := by decide
  have h1 : GT.TFBound (GT.Gad4e6 0 5 8 20) 4 := by decide
  have h2 : GT.TFBound (GT.Gad4e6 0 6 7 11) 4 := by decide
  have h3 : GT.TFBound (GT.Gad4e6 4 13 17 19) 4 := by decide
  have h4 : GT.TFBound (GT.Gad4e6 6 8 14 21) 4 := by decide
  have h5 : GT.TFBound (GT.Gad4e6 9 16 18 19) 4 := by decide
  have h6 : GT.TFBound (GT.Gad3e3 1 3 11) 2 := by decide
  have h7 : GT.TFBound (GT.Gad3e3 1 15 16) 2 := by decide
  have h8 : GT.TFBound (GT.Gad3e3 2 5 14) 2 := by decide
  have h9 : GT.TFBound (GT.Gad3e3 3 6 19) 2 := by decide
  have h10 : GT.TFBound (GT.Gad3e3 4 15 18) 2 := by decide
  have h11 : GT.TFBound (GT.Gad3e3 12 19 21) 2 := by decide
  have hr : GT.TFBound rest rest.card := GTP7.proof rest
  exact GTP9.proof _ _ _ _ (GTP8.proof _ _ _ _ h0 (GTP8.proof _ _ _ _ h1 (GTP8.proof _ _ _ _ h2 (GTP8.proof _ _ _ _ h3 (GTP8.proof _ _ _ _ h4 (GTP8.proof _ _ _ _ h5 (GTP8.proof _ _ _ _ h6 (GTP8.proof _ _ _ _ h7 (GTP8.proof _ _ _ _ h8 (GTP8.proof _ _ _ _ h9 (GTP8.proof _ _ _ _ h10 (GTP8.proof _ _ _ _ h11 hr)))))))))))) (by decide +kernel) (by decide +kernel)
end GTCert0
