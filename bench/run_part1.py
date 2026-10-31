#!/usr/bin/env python3
"""Partie 1 : 26 jeux x 2 repetitions, -u 1, sur fixed1. Ordre aleatoire (graine fixe).
Reprenable : un run dont le fichier existe deja (plus de 20 lignes) est saute."""
import csv, json, os, random, subprocess, sys, urllib.request

HOST = os.environ["HOST"]
DUR = os.environ.get("DUR", "60s")
REPS = 2

# (prefixe, U du jeu, facteur, valeur)
DATASETS = (
    [("u100", 100, "U", 100), ("base", 1000, "U", 1000), ("u10000", 10000, "U", 10000)]
    + [("p10", 100, "P", 10), ("p100", 100, "P", 100), ("p1000", 100, "P", 1000)]
    + [(f"f{f:02d}", 120, "F", f) for f in range(5, 101, 5)]
)
os.makedirs("raw", exist_ok=True)

def check(prefix):
    url = f"{HOST}/api/timeline?user={prefix}_u00000&limit=20"
    with urllib.request.urlopen(url, timeout=60) as r:
        body = json.load(r)
        return body["count"], r.headers.get("X-Instance"), r.headers.get("Server-Timing")

def done(path):
    return os.path.exists(path) and sum(1 for _ in open(path)) > 20

def locust(prefix, n_users, log):
    if done(log):
        print(f"[saute] {log} existe deja", flush=True)
        return
    env = dict(os.environ, TINY_PREFIX=prefix, TINY_USERS=str(n_users), TINY_LOG=log)
    subprocess.run(["locust", "-f", "bench/locustfile.py", "--headless", "-u", "1", "-r", "1",
                    "-t", DUR, "--only-summary", "--host", HOST], env=env, check=True)

# 1) verification : chaque jeu renvoie 20 posts
with open("raw/p1_check.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["dataset", "count", "instance", "server_timing"])
    for prefix, *_ in DATASETS:
        c, inst, st = check(prefix)
        w.writerow([prefix, c, inst, st])
        if c != 20:
            sys.exit(f"STOP : {prefix} renvoie count={c}")
print("verifications OK", flush=True)

# 2) run de chauffe (jete)
locust("base", 1000, "raw/p1_warmup.csv")

# 3) les 52 runs, ordre aleatoire reproductible
runs = [(d, r) for d in DATASETS for r in range(1, REPS + 1)]
random.Random(2026).shuffle(runs)
with open("raw/p1_order.txt", "w") as f:
    for (prefix, *_), r in runs:
        f.write(f"{prefix} r{r}\n")
for i, ((prefix, n_users, *_), r) in enumerate(runs, 1):
    print(f"=== [{i}/{len(runs)}] {prefix} r{r} ===", flush=True)
    locust(prefix, n_users, f"raw/p1_{prefix}_r{r}.csv")
print("CAMPAGNE TERMINEE", flush=True)
