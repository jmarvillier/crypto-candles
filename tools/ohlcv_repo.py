"""Socle commun du repo OHLCV : conventions de chemins, TF, I/O NDJSON, fusion, méta.

Format de ligne (NDJSON, une bougie par ligne, ordre chronologique croissant) :
    [ts, open, high, low, close, vol_base, vol_quote, src]
  ts        open time, epoch ms, UTC
  vol_base  volume en actif de base   (OKX volCcy)
  vol_quote volume en quote           (OKX volCcyQuote)
  src       "x" = XPERP EEA, "s" = perp classique USDT, "d" = derive par agregation

Seules les bougies CLOSES sont ecrites (OKX confirm == "1").
"""
import json
import os
from datetime import datetime, timezone, timedelta

COLUMNS = ["ts", "open", "high", "low", "close", "vol_base", "vol_quote", "src"]

# bar     = valeur du parametre `bar` de l'API OKX (None => derive)
# ms      = duree nominale d'une bougie (None => calendaire, pas de grille fixe)
# shard   = decoupage des fichiers : "month" | "year" | "single"
#
# Regle : sous-repertoire annuel pour TOUT ce qui est sous l'hebdomadaire, afin
# que la structure soit uniforme et previsible quand on parcourt le repo a la
# main. Le 1min descend au mois (2,7 Mo par mois, un fichier annuel serait trop
# gros). A partir du 1w, fichier unique : une bougie hebdomadaire peut chevaucher
# deux annees (semaine du 30/12) et une bougie annuelle n'appartient a aucun
# repertoire d'annee — sharder la produirait une convention arbitraire qu'il
# faudrait connaitre pour lire correctement.
TF_TABLE = {
    "1min":  {"bar": "1m",     "ms": 60_000,      "shard": "month"},
    "5min":  {"bar": "5m",     "ms": 300_000,     "shard": "year"},
    "15min": {"bar": "15m",    "ms": 900_000,     "shard": "year"},
    "30min": {"bar": "30m",    "ms": 1_800_000,   "shard": "year"},
    "1h":    {"bar": "1H",     "ms": 3_600_000,   "shard": "year"},
    "4h":    {"bar": "4H",     "ms": 14_400_000,  "shard": "year"},
    "12h":   {"bar": "12Hutc", "ms": 43_200_000,  "shard": "year"},
    "1d":    {"bar": "1Dutc",  "ms": 86_400_000,  "shard": "year"},
    "1w":    {"bar": "1Wutc",  "ms": 604_800_000, "shard": "single"},
    "1mon":  {"bar": "1Mutc",  "ms": None,        "shard": "single"},
    "1y":    {"bar": None,     "ms": None,        "shard": "single",
              "derived_from": "1mon"},
}

ALL_TFS = list(TF_TABLE)
NATIVE_TFS = [t for t, c in TF_TABLE.items() if c["bar"]]
DERIVED_TFS = [t for t, c in TF_TABLE.items() if not c["bar"]]


# --------------------------------------------------------------------------
# temps
# --------------------------------------------------------------------------
def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_ms(s):
    """Accepte 'YYYY-MM-DD', 'YYYY-MM', 'YYYY', ISO complet, ou un epoch ms."""
    if s is None:
        return None
    s = str(s).strip()
    if s.isdigit() and len(s) >= 10:
        return int(s)
    for fmt, pad in (("%Y-%m-%dT%H:%M:%S", None), ("%Y-%m-%d", None),
                     ("%Y-%m", None), ("%Y", None)):
        try:
            d = datetime.strptime(s.replace("Z", ""), fmt)
            return int(d.replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError("date illisible: %r" % s)


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# --------------------------------------------------------------------------
# chemins
# --------------------------------------------------------------------------
# Les deux sources vivent dans des arborescences SEPAREES. XPERP et perp
# classique ne cotent pas au meme prix : les fusionner fabriquerait une serie
# qui traverse un saut de prix artificiel. Separees, chacune est homogene et
# directement backtestable.
SOURCES = {"xperp": "x", "perp": "s"}


def asset_dir(repo, asset):
    return os.path.join(repo, "data", asset.upper())


def source_dir(repo, asset, source):
    if source not in SOURCES:
        raise ValueError("source inconnue %r (attendu : %s)"
                         % (source, ", ".join(SOURCES)))
    return os.path.join(asset_dir(repo, asset), source)


def tf_dir(repo, asset, source, tf):
    return os.path.join(source_dir(repo, asset, source), tf)


def shard_path(repo, asset, source, tf, ts):
    """Fichier qui doit accueillir la bougie d'open time `ts`."""
    cfg = TF_TABLE[tf]
    d = datetime.fromtimestamp(ts / 1000, timezone.utc)
    base = tf_dir(repo, asset, source, tf)
    if cfg["shard"] == "month":
        return os.path.join(base, "%04d" % d.year, "%04d-%02d.ndjson" % (d.year, d.month))
    if cfg["shard"] == "year":
        return os.path.join(base, "%04d" % d.year, "%04d.ndjson" % d.year)
    return os.path.join(base, "%s.ndjson" % tf)


def list_shards(repo, asset, source, tf):
    base = tf_dir(repo, asset, source, tf)
    out = []
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".ndjson"):
                out.append(os.path.join(root, f))
    return sorted(out)


def list_assets(repo):
    d = os.path.join(repo, "data")
    if not os.path.isdir(d):
        return []
    return sorted(p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p)))


def list_sources(repo, asset):
    """Sources reellement peuplees pour cet actif."""
    out = []
    for s in SOURCES:
        d = source_dir(repo, asset, s)
        if os.path.isdir(d) and any(
                f.endswith(".ndjson") for _r, _dd, fs in os.walk(d) for f in fs):
            out.append(s)
    return out


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------
def read_shard(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("%s ligne %d illisible: %s" % (path, n, e))
    return rows


def write_shard(path, rows):
    """Ecriture atomique, trie et dedupliquee. Derniere source gagne sur un doublon."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    by_ts = {}
    for r in rows:
        by_ts[int(r[0])] = r
    ordered = [by_ts[k] for k in sorted(by_ts)]
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        for r in ordered:
            fh.write(json.dumps(r, separators=(",", ":")) + "\n")
    os.replace(tmp, path)
    return len(ordered)


def read_range(repo, asset, source, tf, start_ms=None, end_ms=None):
    """Toutes les bougies d'un TF sur [start, end[, chronologiques."""
    rows = []
    for p in list_shards(repo, asset, source, tf):
        for r in read_shard(p):
            ts = int(r[0])
            if start_ms is not None and ts < start_ms:
                continue
            if end_ms is not None and ts >= end_ms:
                continue
            rows.append(r)
    rows.sort(key=lambda r: int(r[0]))
    return rows


def grid_offset(tf):
    """Residu attendu de ts % step.

    Vaut 0 pour tous les TF sauf l'hebdomadaire : epoch 0 (1970-01-01) etait un
    JEUDI, or les bougies weekly OKX ouvrent le lundi. Le residu attendu est
    donc 4 jours, pas 0 — un controle naif `ts % step == 0` produit un faux
    positif sur 100 % des bougies 1w.
    """
    return 4 * 86_400_000 if tf == "1w" else 0


def merge_rows(repo, asset, source, tf, new_rows):
    """Fusionne des bougies dans les shards concernes.

    Les deux sources etant separees, il n'y a plus d'arbitrage entre elles :
    une collision ne peut venir que d'un refetch de la meme serie. La derniere
    valeur gagne, mais une bougie a volume nul ne remplace jamais une bougie a
    volume reel (un refetch pendant une coupure de cotation renverrait des
    bougies plates).
    Retourne (n_ajoutees, n_ignorees, [fichiers touches]).
    """
    buckets = {}
    for r in new_rows:
        buckets.setdefault(shard_path(repo, asset, source, tf, int(r[0])), []).append(r)

    added = skipped = 0
    touched = []
    for path, rows in buckets.items():
        existing = read_shard(path)
        idx = {int(r[0]): r for r in existing}
        changed = False
        for r in rows:
            ts = int(r[0])
            old = idx.get(ts)
            if old is not None:
                if old == r or (float(r[5]) == 0 and float(old[5]) > 0):
                    skipped += 1
                    continue
            else:
                added += 1
            idx[ts] = r
            changed = True
        if changed:
            write_shard(path, list(idx.values()))
            touched.append(path)
    return added, skipped, touched


# --------------------------------------------------------------------------
# integrite
# --------------------------------------------------------------------------
def find_gaps(rows, step_ms, max_report=50):
    """Trous sur une grille reguliere. Retourne [(ts_apres, ts_avant, n_manquantes)]."""
    if not step_ms or len(rows) < 2:
        return []
    gaps = []
    for a, b in zip(rows, rows[1:]):
        ta, tb = int(a[0]), int(b[0])
        missing = (tb - ta) // step_ms - 1
        if missing > 0:
            gaps.append((ta, tb, int(missing)))
            if len(gaps) >= max_report:
                break
    return gaps


def check_rows(rows):
    """Anomalies structurelles : OHLC incoherent, negatifs, doublons, desordre."""
    errs = []
    seen = set()
    prev = None
    for r in rows:
        ts = int(r[0])
        if ts in seen:
            errs.append("doublon ts=%s" % iso(ts))
        seen.add(ts)
        if prev is not None and ts < prev:
            errs.append("desordre ts=%s" % iso(ts))
        prev = ts
        o, h, l, c = (float(r[i]) for i in range(1, 5))
        if not (l <= o <= h and l <= c <= h):
            errs.append("OHLC incoherent ts=%s (o=%s h=%s l=%s c=%s)" % (iso(ts), o, h, l, c))
        if min(o, h, l, c) <= 0:
            errs.append("prix <= 0 ts=%s" % iso(ts))
        if float(r[5]) < 0 or float(r[6]) < 0:
            errs.append("volume negatif ts=%s" % iso(ts))
        if len(r) != 8:
            errs.append("arite %d != 8 ts=%s" % (len(r), iso(ts)))
    return errs


def tf_meta(repo, asset, source, tf):
    rows = read_range(repo, asset, source, tf)
    if not rows:
        return {"tf": tf, "n_rows": 0}
    gaps = find_gaps(rows, TF_TABLE[tf]["ms"])
    return {
        "tf": tf,
        "n_rows": len(rows),
        "first_ts": int(rows[0][0]),
        "first": iso(int(rows[0][0])),
        "last_ts": int(rows[-1][0]),
        "last": iso(int(rows[-1][0])),
        "n_gaps": len(gaps),
        "missing_candles": sum(g[2] for g in gaps),
        "n_zero_volume": sum(1 for r in rows if float(r[5]) == 0),
        "gaps_sample": [{"after": iso(a), "before": iso(b), "missing": n}
                        for a, b, n in gaps[:10]],
    }


def write_source_meta(repo, asset, source, extra=None):
    meta = {
        "asset": asset.upper(),
        "source": source,
        "updated_at": iso(now_ms()),
        "columns": COLUMNS,
        "timeframes": {},
    }
    if extra:
        meta.update(extra)
    for tf in ALL_TFS:
        if os.path.isdir(tf_dir(repo, asset, source, tf)):
            m = tf_meta(repo, asset, source, tf)
            if m["n_rows"]:
                meta["timeframes"][tf] = m
    path = os.path.join(source_dir(repo, asset, source), "_meta.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return meta


def read_source_meta(repo, asset, source):
    path = os.path.join(source_dir(repo, asset, source), "_meta.json")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def cutoff(repo, asset, source, tf):
    """Open time de la derniere bougie stockee, ou None. Base de l'update."""
    shards = list_shards(repo, asset, source, tf)
    if not shards:
        return None
    rows = read_shard(shards[-1])
    return int(rows[-1][0]) if rows else None


# --------------------------------------------------------------------------
# agregation (pour les TF derives : 1y)
# --------------------------------------------------------------------------
def aggregate_calendar(rows, unit="year"):
    """Agrege des bougies en bougies calendaires (year ou month). src -> 'd'."""
    buckets = {}
    for r in rows:
        d = datetime.fromtimestamp(int(r[0]) / 1000, timezone.utc)
        key = d.year if unit == "year" else (d.year, d.month)
        buckets.setdefault(key, []).append(r)
    out = []
    for key in sorted(buckets):
        grp = sorted(buckets[key], key=lambda r: int(r[0]))
        if unit == "year":
            start = datetime(key, 1, 1, tzinfo=timezone.utc)
        else:
            start = datetime(key[0], key[1], 1, tzinfo=timezone.utc)
        out.append([
            int(start.timestamp() * 1000),
            float(grp[0][1]),
            max(float(r[2]) for r in grp),
            min(float(r[3]) for r in grp),
            float(grp[-1][4]),
            round(sum(float(r[5]) for r in grp), 8),
            round(sum(float(r[6]) for r in grp), 8),
            "d",
        ])
    return out
