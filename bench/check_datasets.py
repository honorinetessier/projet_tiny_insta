import warnings
warnings.filterwarnings("ignore")
from google.cloud import datastore
from google.cloud.datastore.query import PropertyFilter

c = datastore.Client()

EXPECTED = [
    ("u100", 100, 20, 20), ("base", 1000, 20, 20), ("u10000", 10000, 20, 20),
    ("p10", 100, 10, 20), ("p100", 100, 100, 20), ("p1000", 100, 1000, 20),
]
EXPECTED += [(f"f{f:02d}", 120, 20, f) for f in range(5, 101, 5)]

for prefix, U, P, F in EXPECTED:
    first = f"{prefix}_u00000"
    last = f"{prefix}_u{U - 1:05d}"
    beyond = f"{prefix}_u{U:05d}"

    e_first = c.get(c.key("User", first))
    e_last = c.get(c.key("User", last))
    e_beyond = c.get(c.key("User", beyond))

    if e_first is None:
        print(f"{prefix:7s} ABSENT")
        continue

    problems = []
    if e_last is None:
        problems.append(f"dernier utilisateur {last} absent")
    if e_beyond is not None:
        problems.append(f"{beyond} existe : U est trop grand")
    if len(e_first["follows"]) != F:
        problems.append(f"F={len(e_first['follows'])} au lieu de {F}")

    q = c.query(kind="Post")
    q.add_filter(filter=PropertyFilter("author", "=", first))
    q.keys_only()
    n_posts = len(list(q.fetch()))
    if n_posts != P:
        problems.append(f"P={n_posts} au lieu de {P}")

    print(f"{prefix:7s}", "OK" if not problems else "PROBLEME : " + " ; ".join(problems))
