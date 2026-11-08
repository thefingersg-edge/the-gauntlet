"""Run the staged harness end-to-end on synthetic data (planted drift) in a temp SS_DATA dir."""
import os, sys, tempfile, zipfile, hashlib, subprocess, shutil
root = tempfile.mkdtemp(); os.environ["SS_DATA"] = root
import synth_test
synth_test.make(root, drift=True, N=300, T=1800)
raw = os.path.join(root, "raw")
with zipfile.ZipFile(os.path.join(raw, "stocks.csv.zip"), "w") as z: z.write(os.path.join(raw, "stocks.csv"), "SHARADAR_SEP.csv")
os.remove(os.path.join(raw, "stocks.csv"))
import pead_engine as E; E.BANDS = (("L", 100), ("M", 100), ("S", 100))
import pead1_run as R
doc = os.path.join(root, "PRE.md"); open(doc, "w").write("test")
R.DOC = (doc, hashlib.sha256(b"test").hexdigest()); R.PIN_CODE = {}; R.CHUNK = 100
for st in ("unzip", "store", "store", "bands", "bench", "events", "final"):
    sys.argv = ["x", st]; R.main()
shutil.rmtree(root)
