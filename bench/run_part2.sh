#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

# Sécurité : vérifier le projet Google Cloud
if [[ "$(gcloud config get-value project 2>/dev/null)" != "tiny-insta-510113" ]]; then
  echo "ERREUR : mauvais projet Google Cloud."
  exit 1
fi

command -v locust >/dev/null || {
  echo "Locust absent : pip install -r bench/requirements.txt"
  exit 1
}

mkdir -p raw
current=""

# Arrêter la version en cours, même si le script échoue
cleanup() {
  code=$?
  trap - EXIT INT TERM
  if [[ -n "$current" ]]; then
    echo "Arrêt de sécurité de $current..."
    gcloud app versions stop "$current" --service=default --quiet || true
  fi
  exit "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Tester successivement 1, 2 et 4 instances
for n in 1 2 4; do
  version="fixed$n"
  current="$version"
  echo "===== N=$n : $version ====="

  # Utiliser la version existante ou la déployer
  if gcloud app versions describe "$version" --service=default >/dev/null 2>&1; then
    status=$(gcloud app versions describe "$version" --service=default --format='value(servingStatus)')
    if [[ "$status" != "SERVING" ]]; then
      gcloud app versions start "$version" --service=default --quiet
    fi
  else
    bash ./deploy_fixed.sh "$n"
  fi

  url=$(gcloud app versions describe "$version" --service=default --format='value(versionUrl)')
  echo "Adresse : $url"

  # Vérifier que le jeu base renvoie bien 20 posts
  count=""
  for i in 1 12; do
    count=$(curl -fsS --max-time 30 "$url/api/timeline?user=base_u00000&limit=20" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["count"])') || count=""
    [[ "$count" == "20" ]] && break
    sleep 5
  done
  [[ "$count" == "20" ]] || {
    echo "ERREUR : la timeline ne contient pas 20 posts"
    exit 1
  }

  # Chauffe de 15 secondes
  echo "Chauffe de $version..."
  TINY_PREFIX=base TINY_USERS=1000 TINY_LOG="raw/p2_warmup_n${n}.csv" \
    locust -f bench/locustfile.py --headless \
    -u 1 -r 1 -t 15s --only-summary --exit-code-on-error 0 --host "$url"

  # 7 concurrences, 2 répétitions chacune
  for c in 1 2 4 8 16 32 64; do
    for r in 1 2; do
      log="raw/p2_n${n}_c${c}_r${r}.csv"

      # Ne pas refaire les tests déjà enregistrés
      if [[ -f "$log" ]] && (( $(wc -l < "$log") > 20 )); then
        echo "Déjà mesuré : $log (ignoré)"
        continue
      fi

      # Vérifier le nombre d'instances actives
      instances=$(gcloud app instances list --service=default --version="$version" \
        --format='value(id)' | awk 'NF {n++} END {print n+0}')

      echo "N=$n C=$c répétition=$r : $instances instances actives"

      [[ "$instances" == "$n" ]] || {
        echo "ERREUR : $n instances attendues"
        exit 1
      }

      # Test Locust de 60 secondes
      TINY_PREFIX=base TINY_USERS=1000 TINY_LOG="$log" \
        locust -f bench/locustfile.py --headless \
        -u "$c" -r "$c" -t 60s --only-summary --exit-code-on-error 0 --host "$url"

      # Vérifier les résultats enregistrés
      python3 - "$log" <<'PY'
import csv, sys
with open(sys.argv[1], newline='') as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit("ERREUR : CSV vide")
instances = {r['INSTANCE'] for r in rows if r['INSTANCE']}
fails = sum(r['STATUS'] != '200' for r in rows)
print(f"{len(rows)} requêtes, {fails} échecs HTTP, {len(instances)} instances observées")
PY

    done
  done

  # Arrêter la version avant de passer à la suivante
  echo "Arrêt de $version..."
  gcloud app versions stop "$version" --service=default --quiet
  current=""
done

echo "CAMPAGNE PARTIE 2 TERMINEE. Toutes les versions fixes sont arrêtées."
