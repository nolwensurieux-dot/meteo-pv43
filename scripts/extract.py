"""Construit data.json à partir du fichier Excel de l'équipe, ou d'un CSV Météo-France (Q_43_...csv.gz).
Usage : python3 extract.py <fichier.xlsx | fichier.csv[.gz]> [<autre fichier> ...] > data.json
Plusieurs fichiers peuvent être donnés : les plus récents complètent/écrasent les plus anciens.
"""
import sys, os, json, gzip, csv, io, datetime as dt

# Stations suivies, dans l'ordre du fichier de synthèse.
# alt / x / y : paramètres repris des onglets du fichier (utilisés pour l'ETP AP3C).
STATIONS = [
    ("FONTANNES", "Fontannes", "Fontannes"),
    ("BAS-EN-BASSET", "Bas-en-Basset", "Bas_en_Basset"),
    ("LAVOUTE-CHILHAC", "Lavoûte-Chilhac", "Lavoute_Chilhac"),
    ("MONISTROL-SUR-LOIRE", "Monistrol-sur-Loire", "Monistrol_Sur_Loire"),
    ("YSSINGEAUX", "Yssingeaux", "Yssingeaux"),
    ("ST-PAL-DE-CHALENCON", "St-Pal-de-Chalencon", "St_Pal_De_Chalencon"),
    ("LE PUY-LOUDES", "Chaspuzac", "Le_Puy_Loudes"),
    ("FIX-ST-GENEYS", "Fix-St-Geneys", "Fix_St_Geneys"),
    ("SAUGUES-SA", "Saugues", "Saugues"),
    ("MAZET-VOLAMONT", "Mazet-St-Voy", "Mazet_Volamont"),
    ("FELINES_SAPC", "Félines", "Felines"),
    ("LANDOS-CHARBON", "Landos", "Landos_Charbon"),
    ("LES ESTABLES_SAPC", "Les Estables", "Les_Estables"),
]
ZONES = [
    {"id": "z1", "name": "Fontannes", "stations": ["FONTANNES"]},
    {"id": "z2", "name": "Yssingeaux · St-Pal", "stations": ["YSSINGEAUX", "ST-PAL-DE-CHALENCON"]},
    {"id": "z3", "name": "Chaspuzac · Fix · Saugues", "stations": ["LE PUY-LOUDES", "FIX-ST-GENEYS", "SAUGUES-SA"]},
    {"id": "z4", "name": "Mazet · Félines · Les Estables", "stations": ["MAZET-VOLAMONT", "FELINES_SAPC", "LES ESTABLES_SAPC"]},
]
PARAMS_FILE = os.path.join(os.environ.get("TMPDIR", "/tmp"), "pv43_stations_params.json")


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def read_xlsx(path, rows, params):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["DataMeteo"]
    for r in ws.iter_rows(min_row=2, max_col=5, values_only=True):
        if not r[0] or not r[1]:
            continue
        rows[(r[0].strip(), r[1].date().isoformat())] = (num(r[2]), num(r[3]), num(r[4]))
    for code, _, sheet in STATIONS:
        if sheet in wb.sheetnames and not params.get(code, {}).get("official"):
            ws = wb[sheet]
            params[code] = {"alt": ws["R4"].value, "x": ws["V3"].value, "y": ws["V4"].value}


def lambert93(lat, lon):
    """WGS84/RGF93 -> Lambert-93 (formules IGN)."""
    from math import radians, log, tan, pi, sin, sqrt, exp, atan, cos
    a, e = 6378137.0, 0.0818191910428158
    l0, p0, p1, p2, x0, y0 = radians(3), radians(46.5), radians(44), radians(49), 700000, 6600000
    lat_iso = lambda p: log(tan(pi / 4 + p / 2) * ((1 - e * sin(p)) / (1 + e * sin(p))) ** (e / 2))
    N = lambda p: a / sqrt(1 - e * e * sin(p) ** 2)
    n = log(N(p2) * cos(p2) / (N(p1) * cos(p1))) / (lat_iso(p1) - lat_iso(p2))
    c = N(p1) * cos(p1) / n * exp(n * lat_iso(p1))
    ys = y0 + c * exp(-n * lat_iso(p0))
    L = lat_iso(radians(lat)); g = n * (radians(lon) - l0)
    r = c * exp(-n * L)
    return x0 + r * sin(g), ys - r * cos(g)


def read_csv(path, rows, params=None):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    rd = csv.DictReader(io.StringIO(raw.decode("utf-8", "replace")), delimiter=";")
    wanted = {c for c, _, _ in STATIONS}
    for r in rd:
        name = (r.get("NOM_USUEL") or "").strip()
        if name not in wanted:
            continue
        d = r["AAAAMMJJ"].strip()
        rows[(name, f"{d[:4]}-{d[4:6]}-{d[6:8]}")] = (num(r.get("RR")), num(r.get("TN")), num(r.get("TX")))
        if params is not None and r.get("ALTI"):
            x, y = lambert93(float(r["LAT"]), float(r["LON"]))
            params[name] = {"alt": float(r["ALTI"]), "x": round(x, 2), "y": round(y, 2),
                            "num": r["NUM_POSTE"].strip(), "official": True}


def main(paths):
    rows, params = {}, {}
    try:
        params.update(json.load(open(PARAMS_FILE)))
    except FileNotFoundError:
        pass
    for p in paths:
        if p.endswith((".xlsx", ".xlsm")):
            read_xlsx(p, rows, params)
        else:
            read_csv(p, rows, params)
    json.dump(params, open(PARAMS_FILE, "w"), indent=1)

    dates = sorted({d for (_, d) in rows})
    start = dt.date.fromisoformat(dates[0])
    # dernière date où au moins la moitié des stations ont une température
    by_date = {}
    for (n, d), (rr, tn, tx) in rows.items():
        if tn is not None and tx is not None:
            by_date[d] = by_date.get(d, 0) + 1
    as_of = max(d for d, c in by_date.items() if c >= len(STATIONS) / 2)
    n_days = (dt.date.fromisoformat(as_of) - start).days + 1

    out = []
    for code, name, _ in STATIONS:
        rr, tn, tx = [], [], []
        for k in range(n_days):
            d = (start + dt.timedelta(days=k)).isoformat()
            v = rows.get((code, d), (None, None, None))
            rr.append(v[0]); tn.append(v[1]); tx.append(v[2])
        p = params.get(code, {"alt": 833, "x": 760086.53, "y": 6441954.05})
        out.append({"code": code, "name": name, "alt": p["alt"], "x": p["x"], "y": p["y"], "official": bool(p.get("official")),
                    "start": start.isoformat(), "rr": rr, "tn": tn, "tx": tx})
    return {"asOf": as_of, "builtAt": dt.datetime.now().isoformat(timespec="minutes"),
            "stations": out, "zones": ZONES}


if __name__ == "__main__":
    json.dump(main(sys.argv[1:]), sys.stdout, separators=(",", ":"), ensure_ascii=False)
