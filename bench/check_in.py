import time, warnings
warnings.filterwarnings("ignore")
from google.cloud import datastore

c = datastore.Client()
print("Le client a une méthode gql :", hasattr(c, "gql"))

for F in range(5, 101, 5):
    prefix = f"f{F:02d}"
    user = f"{prefix}_u00000"
    entity = c.get(c.key("User", user))
    authors = list({*entity["follows"], user})

    q = c.query(kind="Post")
    q.add_filter("author", "IN", authors)
    q.order = ["-created"]
    t0 = time.perf_counter()
    try:
        posts = list(q.fetch(limit=20))
        ms = (time.perf_counter() - t0) * 1000
        print(f"{prefix}: {len(authors):3d} auteurs -> IN OK, {len(posts)} posts, {ms:.0f} ms")
    except Exception as ex:
        print(f"{prefix}: {len(authors):3d} auteurs -> ERREUR {type(ex).__name__}: {str(ex)[:150]}")
