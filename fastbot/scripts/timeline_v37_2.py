#!/usr/bin/env python3
"""PREREGISTRATION_v37.2 -- v37.1 unchanged, on the rebuilt timeline
(tl_build 1.1, VX dates fixed). Checks the v37.2 document and the matrix sha."""
import hashlib, os, sys
import timeline_v37_1 as M

DOC2 = ("PREREGISTRATION_v37.2.md", "2bc90f6dd33478daa83464ebe4269bb1dded0d90810f5ad522d0bb288dfac28c")
MATRIX_SHA = "6fc354b289c94cbf28b018e5f233e22d949c1f23cc6aeff3bc88aced09ce2088"
here = os.path.dirname(os.path.abspath(__file__))
for path, want in ((os.path.join(here, "..", DOC2[0]), DOC2[1]),
                   (os.path.join(here, M.MAT), MATRIX_SHA)):
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != want:
        print(f"  {os.path.basename(path)} does not match v37.2. Refused."); sys.exit(2)
print(f"  PREREGISTRATION_v37.2.md and matrix.npz match their frozen sha256")
M.LOCK = "../data/timeline_v37/LOCK_v37_2.pkl"
M.VERSION = "1.1.1 via timeline_v37_2"
M.main()
