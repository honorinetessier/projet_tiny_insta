#!/usr/bin/env python3
"""Partie 2 : mesures de capacité pour UNE version fixedN.
Usage : python bench/run_part2.py N [--dry]   (N = 1, 2 ou 4)"""
import argparse, json, os, random, subprocess, urllib.request
import pandas as pd

DOMAIN = os.environ.get("DOMAIN", "tiny-insta-510113.lm.r.appspot.com")
CS = [1, 2, 4, 8, 16, 32, 64]
REPS = 2
DUR = os.environ.get("DUR", "60s")
WARMUP_S = 10

ap = argparse.ArgumentParser()
ap.add_argument("n", type=int, choices=[1, 2, 4])
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
N = a.n
HOST = f"https://fixed{N}-dot-{DOMAIN}"
os.makedirs("raw", exist_ok=True)

def locust(c, dur, log):
    env = dict(os.environ, TINY_PREFIX="base", TINY_USERS="1000", TINY_LOG=log)
    subprocess.run(["locust", "-f", "bench/locustfile.py", "--headless",
                    "-u", str(c), "-r", str(c), "-t", dur, "--only-summary",
                    "--host", HOST], env=env, check=True)

def done(path):
    return os.path.exists(path) and sum(1 for _ in open(path)) > 20

def resume(log):
    d = pd.read_csv(log)
    t = d["T_START"] - d["T_START"].min()
    w = d[t >= WARMUP_S]
    ok = w[w["STATUS"] == 200]
    debit = len(ok) / (t.max() - WARMUP_S)
    print(f"   -> {len(w)} requetes, {len(w) - len(ok)} non-200, "
          f"debit ~ {debit:.1f} req/s, latence mediane {ok['LATENCY_MS'].median():.0f} ms, "
          f"instances distinctes : {ok['INSTANCE'].nunique()}", flush=True)

# ordre des 14 runs : melange reproductible (graine = 2026 + N)
runs = [(c, r) for c in CS for r in range(1, REPS + 1)]
random.Random(2026 + N).shuffle(runs)

if a.dry:
    print(f"[dry] version fixed{N}, adresse {HOST}")
    for i, (c, r) in enumerate(runs, 1):
        print(f"[dry] {i:2d}/14  C={c:2d}  rep {r}  -> raw/p2_n{N}_c{c}_r{r}.csv")
    raise SystemExit

# 1) verification : la version repond-elle, avec combien de posts ?
with urllib.request.urlopen(f"{HOST}/api/timeline?user=base_u00000&limit=20", timeout=60) as r:
    body = json.load(r)
    print("verification : count =", body["count"], "| instance =",
          (r.headers.get("X-Instance") or "")[:12], "| Server-Timing =", r.headers.get("Server-Timing"))
if body["count"] != 20:
    raise SystemExit("STOP : la timeline n'a pas 20 posts")

# 2) chauffe : 30 s a C=16, jetee
warm = f"raw/p2_n{N}_warmup.csv"
if not done(warm):
    print("=== chauffe (C=16, 30 s) ===", flush=True)
    locust(16, "30s", warm)
resume(warm)

# 3) les 14 runs
for i, (c, r) in enumerate(runs, 1):
    log = f"raw/p2_n{N}_c{c}_r{r}.csv"
    print(f"=== [{i}/14] fixed{N}  C={c}  rep {r} ===", flush=True)
    if done(log):
        print("   (deja fait, saute)")
    else:
        locust(c, DUR, log)
    resume(log)
print(f"VERSION fixed{N} TERMINEE : pense a lancer  gcloud app versions stop fixed{N}")
