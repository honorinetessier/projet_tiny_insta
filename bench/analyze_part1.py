#!/usr/bin/env python3
import glob, os, re
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

WARMUP_S = 10
os.makedirs("figures", exist_ok=True)
META = {"u100": ("U", 100), "base": ("U", 1000), "u10000": ("U", 10000),
        "p10": ("P", 10), "p100": ("P", 100), "p1000": ("P", 1000)}
META.update({f"f{f:02d}": ("F", f) for f in range(5, 101, 5)})

rows = []
for path in sorted(glob.glob("raw/p1_*_r[0-9]*.csv")):
    m = re.match(r"raw/p1_(.+)_r(\d+)\.csv", path)
    if not m or m.group(1) not in META:
        continue
    prefix, rep = m.group(1), int(m.group(2))
    d = pd.read_csv(path)
    if len(d) == 0:
        continue
    d = d[d["T_START"] - d["T_START"].min() >= WARMUP_S]
    ok = d[d["STATUS"] == 200]
    rows.append(dict(
        dataset=prefix, factor=META[prefix][0], value=META[prefix][1], rep=rep,
        n_requests=len(d), n_errors=len(d) - len(ok),
        n_instances=ok["INSTANCE"].nunique(),
        server_ms=pd.to_numeric(ok["SERVER_MS"], errors="coerce").median(),
        client_ms=ok["LATENCY_MS"].median(),
    ))
runs = pd.DataFrame(rows)
runs.to_csv("figures/p1_runs_detail.csv", index=False)
print("runs analysés :", len(runs), "(attendu : 52)")
print("runs avec erreurs HTTP :", int((runs.n_errors > 0).sum()))
print("instances distinctes par run (valeurs vues) :", sorted(runs.n_instances.unique()))
assert (runs["n_instances"] == 1).all(), "Plus d'une instance a servi : mesure invalide"

agg = (runs.groupby(["factor", "value", "dataset"])
       .agg(server_median_ms=("server_ms", "mean"), client_median_ms=("client_ms", "mean"),
            n_requests=("n_requests", "sum"), n_errors=("n_errors", "sum"),
            n_instances=("n_instances", "max")).reset_index())
agg["client_minus_server_ms"] = agg["client_median_ms"] - agg["server_median_ms"]

s_u = agg[agg.factor == "U"].sort_values("value")
s_p = agg[agg.factor == "P"]
p20 = agg[agg.dataset == "u100"].assign(factor="P", value=20)   # u100 = point P=20
s_p = pd.concat([s_p, p20]).sort_values("value")
s_f = agg[agg.factor == "F"].sort_values("value")

pd.concat([s_u, s_p]).to_csv("figures/fig1a.csv", index=False)
s_f.to_csv("figures/fig1b.csv", index=False)

# Fig 1a
fig, ax = plt.subplots(1, 2, figsize=(9, 3.5), sharey=True)
for a, s, fac, fixe in [(ax[0], s_u, "U", "P=20, F=20"), (ax[1], s_p, "P", "U=100, F=20")]:
    a.plot(s["value"], s["server_median_ms"], "o-")
    a.set_xscale("log"); a.set_xlabel(fac); a.set_title(f"Facteur {fac} (fixe : {fixe})")
ax[0].set_ylabel("temps serveur médian (ms)")
plt.tight_layout(); plt.savefig("figures/fig1a.png", dpi=150); plt.close()

# Fig 1b
plt.figure(figsize=(6.5, 4))
plt.plot(s_f["value"], s_f["server_median_ms"], "o-", label="serveur (Server-Timing)")
plt.plot(s_f["value"], s_f["client_median_ms"], "s-", label="client (Locust)")
plt.axvline(29.5, color="gray", linestyle="--", label="IN refusé à partir de F=30")
plt.xlabel("F (followees)"); plt.ylabel("médiane (ms)")
plt.title("U=120, P=20, fixed1, -u 1"); plt.legend(); plt.tight_layout()
plt.savefig("figures/fig1b.png", dpi=150)

pd.set_option("display.width", 200)
print(agg.sort_values(["factor", "value"]).round(1).to_string(index=False))
