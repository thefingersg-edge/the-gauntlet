import os, time, sys, ss_lib, batchB_engine as B, ss_events2 as S
t0 = time.time(); F = sorted(os.listdir(S.STORE)); done = 0
for f in F:
    if os.path.exists(os.path.join(B.EDGE_DIR, f)): done += 1; continue
    if time.time() - t0 > 160: break
    B.edge_series(f, ss_lib.load(S.STORE, f)); done += 1
print(f"edge cache {done}/{len(F)}")
