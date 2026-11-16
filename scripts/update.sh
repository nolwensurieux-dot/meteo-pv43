#!/bin/bash
# Télécharge les données Météo-France de Haute-Loire et construit l'appli dans site/.
# Usage : PV43_MDP="mot de passe" bash scripts/update.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
# Le nom du fichier "latest" change chaque année : on le retrouve via l'API data.gouv.fr
URL=$(curl -sS -f -m 60 "https://www.data.gouv.fr/api/2/datasets/6569b51ae64326786e4e8e1a/resources/?page_size=1000&type=main" \
  | python3 -c "import json,sys;print([r['url'] for r in json.load(sys.stdin)['data'] if 'Q_43_latest' in r['url'] and 'RR-T-Vent' in r['url']][0])")
echo "Fichier : $URL"
curl -sS -f -m 300 -o "$TMP/Q43.csv.gz" "$URL"
python3 "$ROOT/scripts/extract.py" "$TMP/Q43.csv.gz" > "$TMP/data.json"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('Données jusqu au',d['asOf']);assert len(d['stations'])==13" "$TMP/data.json"
rm -rf "$ROOT/site" && mkdir -p "$ROOT/site"
cp "$ROOT"/static/* "$ROOT/site/"
PV43_PWA=1 python3 "$ROOT/scripts/build.py" "$TMP/data.json" "$PV43_MDP" > "$ROOT/site/index.html"
sed -i "s/__VERSION__/$(date +%Y%m%d%H%M)/" "$ROOT/site/sw.js"
touch "$ROOT/site/.nojekyll"
echo "OK : $(wc -c < "$ROOT/site/index.html") octets"
