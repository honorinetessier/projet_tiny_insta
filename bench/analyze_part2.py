import glob
import os
import re
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("figures", exist_ok=True)
rows = []

# Lecture des 42 fichiers de mesures
for path in sorted(glob.glob("raw/p2_n*_c*_r*.csv")):
    m = re.search(r"p2_n(\d+)_c(\d+)_r(\d+)\.csv$", path)
    if not m:
        continue

    n, c, rep = map(int, m.groups())
    d = pd.read_csv(path)

    # On retire les 10 premières secondes
    t = d["T_START"] - d["T_START"].min()
    d = d[t >= 10].copy()
    duree = t.max() - 10

    ok = d[d["STATUS"] == 200]

    rows.append({
        "N": n,
        "C": c,
        "rep": rep,
        "debit_req_s": len(ok) / duree,
        "latence_mediane_ms": ok["LATENCY_MS"].median(),
        "erreurs": len(d) - len(ok),
        "instances_observees": ok["INSTANCE"].nunique()
    })

runs = pd.DataFrame(rows)
print("Nombre de mesures :", len(runs))

if len(runs) != 42:
    raise ValueError("On attend 42 mesures.")

runs.to_csv("figures/p2_runs_detail.csv", index=False)

# Moyenne des deux répétitions
agg = runs.groupby(["N", "C"]).agg(
    debit_req_s=("debit_req_s", "mean"),
    latence_mediane_ms=("latence_mediane_ms", "mean"),
    erreurs=("erreurs", "sum"),
    instances_observees=("instances_observees", "max")
).reset_index()

# Prédiction de la loi de Little, en millisecondes
agg["little_ms"] = 1000 * agg["C"] / agg["debit_req_s"]

agg.to_csv("figures/fig2a.csv", index=False)
agg.to_csv("figures/fig2b.csv", index=False)

cs = [1, 2, 4, 8, 16, 32, 64]

# FIGURE 2a : débit
plt.figure(figsize=(8, 5))

for n in [1, 2, 4]:
    s = agg[agg["N"] == n].sort_values("C")
    plt.plot(s["C"], s["debit_req_s"], "o-", label=f"N={n}")

plt.xscale("log", base=2)
plt.xticks(cs, cs)
plt.xlabel("Concurrence C")
plt.ylabel("Débit (requêtes/s)")
plt.title("Fig. 2a - Débit selon la concurrence")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("figures/fig2a.png", dpi=150)
plt.close()

# FIGURE 2b : latence et loi de Little
plt.figure(figsize=(9, 5))

for n in [1, 2, 4]:
    s = agg[agg["N"] == n].sort_values("C")
    line, = plt.plot(
        s["C"], s["latence_mediane_ms"], "o-",
        label=f"N={n} mesurée"
    )
    plt.plot(
        s["C"], s["little_ms"], "--",
        color=line.get_color(),
        label=f"N={n} C/débit"
    )

plt.xscale("log", base=2)
plt.xticks(cs, cs)
plt.xlabel("Concurrence C")
plt.ylabel("Latence (ms)")
plt.title("Fig. 2b - Latence et loi de Little")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("figures/fig2b.png", dpi=150)
plt.close()

print("Figures 2a et 2b créées dans figures/")
