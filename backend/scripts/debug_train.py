import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.services import ml

t = time.time()
recs, sems, fails = ml.load()
print(f"1. load(): {len(recs)} catatan, {len(sems)} semester, {time.time()-t:.1f} dtk", flush=True)

t = time.time()
df = ml.build_dataset(recs, sems, fails)
print(f"2. build_dataset(): {len(df)} pasang, {time.time()-t:.1f} dtk", flush=True)

t = time.time()
out = ml.fit_and_evaluate(df)
print(f"3. fit_and_evaluate(): terbaik={out['best']}, {time.time()-t:.1f} dtk", flush=True)
for k, v in out["results"].items():
    print("  ", k, {a: round(b, 3) for a, b in v.items()}, flush=True)
print("baseline", out["baseline"])