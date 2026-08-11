#!/usr/bin/env python3
"""Recupere quelques fichiers du repo depuis GitHub, sans cloner.

Un `git clone` complet coute plus de 130 Mo et plusieurs minutes ; un backtest
sur le daily 2024 a besoin de 28 Ko. Ce script telecharge uniquement les shards
couvrant la periode demandee et les place dans une arborescence locale que
`read_ohlcv.py` sait lire telle quelle.

Le depot etant public, aucun token n'est necessaire.

Exemples
    # inventaire distant, sans rien telecharger
    python fetch_remote.py --list

    # une annee de 1h
    python fetch_remote.py --asset BTC --source perp --tf 1h --from 2024 --to 2025 \
        --dest /tmp/candles

    # trois mois de 1min
    python fetch_remote.py --asset BTC --source perp --tf 1min \
        --from 2024-03 --to 2024-06 --dest /tmp/candles

    # estimer le poids avant de lancer
    python fetch_remote.py --asset BTC --source perp --tf 1min --from 2024 --dry-run

Puis, pour lire les donnees recuperees :
    python read_ohlcv.py --repo /tmp/candles --asset BTC --source perp --tf 1h
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ohlcv_repo as R          # noqa: E402

HEADERS = {"User-Agent": "crypto-candles/1.0"}
SECRETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "secrets.json")


def default_base():
    """URL raw du depot, lue dans secrets.json (owner/repo/branch)."""
    if os.path.exists(SECRETS):
        try:
            gh = json.load(open(SECRETS)).get("github", {})
            if gh.get("owner") and gh.get("repo"):
                return "https://raw.githubusercontent.com/%s/%s/%s/" % (
                    gh["owner"], gh["repo"], gh.get("branch", "main"))
        except (ValueError, OSError):
            pass
    return None


def get(url, quiet=False):
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError("HTTP %d sur %s" % (e.code, url))
    except urllib.error.URLError as e:
        raise RuntimeError("reseau : %s (%s)" % (e, url))


def remote_meta(base, asset, source):
    raw = get(base + "data/%s/%s/_meta.json" % (asset.upper(), source))
    return json.loads(raw) if raw else None


def wanted_paths(asset, source, tf, start, end):
    """Chemins relatifs des shards couvrant [start, end[.

    On calcule les chemins au lieu de lister le distant : GitHub n'expose pas
    de listing recursif bon marche, et les noms sont deterministes.
    """
    cfg = R.TF_TABLE[tf]
    base = "data/%s/%s/%s/" % (asset.upper(), source, tf)
    if cfg["shard"] == "single":
        return [base + "%s.ndjson" % tf]

    s = datetime.fromtimestamp(start / 1000, timezone.utc)
    e = datetime.fromtimestamp((end - 1) / 1000, timezone.utc)
    out = []
    if cfg["shard"] == "year":
        for y in range(s.year, e.year + 1):
            out.append(base + "%04d/%04d.ndjson" % (y, y))
    else:
        y, m = s.year, s.month
        while (y, m) <= (e.year, e.month):
            out.append(base + "%04d/%04d-%02d.ndjson" % (y, y, m))
            m += 1
            if m == 13:
                y, m = y + 1, 1
    return out


def cmd_list(base):
    raw = get(base + "meta/instruments.json")
    if raw is None:
        sys.exit("depot introuvable ou vide a %s" % base)
    for asset in sorted(json.loads(raw)):
        print(asset)
        for source in R.SOURCES:
            meta = remote_meta(base, asset, source)
            if not meta:
                continue
            tfs = meta.get("timeframes", {})
            print("  %-6s %-28s %d TF" % (source, meta.get("instId", "?"), len(tfs)))
            for tf, t in tfs.items():
                print("     %-5s %8d  %s -> %s"
                      % (tf, t["n_rows"], t["first"][:10], t["last"][:10]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=None,
                    help="URL raw du depot (defaut : deduit de secrets.json)")
    ap.add_argument("--list", action="store_true", help="inventaire distant")
    ap.add_argument("--asset", "--pair", dest="asset")
    ap.add_argument("--source", choices=["xperp", "perp"])
    ap.add_argument("--tf")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--dest", default="./candles",
                    help="repertoire local a alimenter (defaut : ./candles)")
    ap.add_argument("--dry-run", action="store_true",
                    help="liste et pese les fichiers sans les ecrire")
    ap.add_argument("--tools", action="store_true",
                    help="recuperer aussi tools/ et SPEC.md")
    args = ap.parse_args()

    base = args.base_url or default_base()
    if not base:
        sys.exit("URL du depot inconnue : renseigner owner/repo dans secrets.json "
                 "ou passer --base-url")
    if not base.endswith("/"):
        base += "/"

    if args.list:
        return cmd_list(base)

    missing = [n for n, v in (("--asset", args.asset), ("--source", args.source),
                              ("--tf", args.tf)) if not v]
    if missing:
        sys.exit("manquant : %s (ou utiliser --list)" % ", ".join(missing))
    if args.tf not in R.TF_TABLE:
        sys.exit("TF inconnu %r (connus : %s)" % (args.tf, ", ".join(R.ALL_TFS)))

    # Borner sur la couverture reelle evite de demander des annees inexistantes
    # et de compter des 404 comme des erreurs.
    meta = remote_meta(base, args.asset, args.source)
    if meta is None:
        sys.exit("%s/%s absent du depot distant" % (args.asset.upper(), args.source))
    tmeta = meta.get("timeframes", {}).get(args.tf)
    if not tmeta:
        sys.exit("%s/%s : TF %s absent (disponibles : %s)"
                 % (args.asset.upper(), args.source, args.tf,
                    ", ".join(meta.get("timeframes", {}))))

    start = max(R.to_ms(args.start) or tmeta["first_ts"], tmeta["first_ts"])
    end = min(R.to_ms(args.end) or tmeta["last_ts"] + 1, tmeta["last_ts"] + 1)
    if start >= end:
        sys.exit("periode vide : le distant couvre %s -> %s"
                 % (tmeta["first"][:10], tmeta["last"][:10]))

    paths = wanted_paths(args.asset, args.source, args.tf, start, end)
    print("%s/%s/%s : %d fichier(s) pour %s -> %s"
          % (args.asset.upper(), args.source, args.tf, len(paths),
             R.iso(start)[:10], R.iso(end - 1)[:10]))

    total = rows = 0
    t0 = time.time()
    for rel in paths:
        blob = get(base + rel)
        if blob is None:
            print("  absent  %s" % rel)
            continue
        total += len(blob)
        n = blob.count(b"\n")
        rows += n
        print("  %7.1f Ko  %6d lignes  %s" % (len(blob) / 1024, n, rel))
        if args.dry_run:
            continue
        dst = os.path.join(args.dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(blob)

    if args.tools and not args.dry_run:
        for rel in ["SPEC.md"] + ["tools/%s" % f for f in
                                  ("ohlcv_repo.py", "read_ohlcv.py", "validate.py")]:
            blob = get(base + rel)
            if blob:
                dst = os.path.join(args.dest, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as fh:
                    fh.write(blob)
                print("  + %s" % rel)

    print("\n%s : %.1f Mo, %d bougies, %.1f s"
          % ("Simulation" if args.dry_run else "Recupere",
             total / 1024 / 1024, rows, time.time() - t0))
    if not args.dry_run:
        # _meta.json local : read_ohlcv --list fonctionne sur la copie partielle
        dst = os.path.join(args.dest, "data", args.asset.upper(), args.source,
                           "_meta.json")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        meta["partial"] = "copie partielle recuperee via fetch_remote.py"
        with open(dst, "w") as fh:
            json.dump(meta, fh, indent=2)
        print("Lire : python read_ohlcv.py --repo %s --asset %s --source %s --tf %s"
              % (args.dest, args.asset.upper(), args.source, args.tf))


if __name__ == "__main__":
    main()
