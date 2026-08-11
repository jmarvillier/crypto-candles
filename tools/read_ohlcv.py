#!/usr/bin/env python3
"""Lecture des donnees du repo — le point d'entree pour les backtests.

Chaque serie est homogene : une source, un instrument, aucun saut de prix
artificiel. Le choix de la source est donc un choix de dessin d'experience, pas
un detail technique :

  perp   historique profond (jusqu'a 2020) sur le perp classique USDT.
         Sert a construire et valider une strategie.
  xperp  l'instrument reellement trade sur le compte EEA, mais quelques mois
         seulement. Sert a verifier qu'un edge survit sur l'instrument cible.

Exemples
    python read_ohlcv.py --repo . --list
    python read_ohlcv.py --repo . --asset BTC --source perp --tf 1h \
        --from 2022-01-01 --to 2025-01-01 --format csv -o btc1h.csv
    python read_ohlcv.py --repo . --asset BTC --source xperp --tf 5min --format stats

En Python :
    from read_ohlcv import load
    rows = load(".", "BTC", "perp", "1h", "2022-01-01", "2025-01-01")
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ohlcv_repo as R          # noqa: E402


def load(repo, asset, source, tf, start=None, end=None):
    """Retourne [[ts, o, h, l, c, vol_base, vol_quote, src], ...]."""
    if tf not in R.TF_TABLE:
        raise ValueError("TF inconnu %r (connus : %s)" % (tf, ", ".join(R.ALL_TFS)))
    return R.read_range(repo, asset, source, tf, R.to_ms(start), R.to_ms(end))


def load_dicts(repo, asset, source, tf, start=None, end=None):
    return [dict(zip(R.COLUMNS, r))
            for r in load(repo, asset, source, tf, start, end)]


def resolve_source(repo, asset, requested):
    """Evite le choix implicite : si l'actif a deux sources, il faut trancher."""
    available = R.list_sources(repo, asset)
    if not available:
        raise SystemExit("aucune donnee pour %s" % asset.upper())
    if requested:
        if requested not in available:
            raise SystemExit("source %s absente pour %s (disponibles : %s)"
                             % (requested, asset.upper(), ", ".join(available)))
        return requested
    if len(available) == 1:
        return available[0]
    raise SystemExit(
        "%s contient %s. Preciser --source : le choix change la periode "
        "couverte ET l'instrument, donc le sens du backtest."
        % (asset.upper(), " et ".join(available)))


def stats(rows, tf):
    if not rows:
        return {"n_rows": 0, "warning": "aucune bougie sur cette periode"}
    gaps = R.find_gaps(rows, R.TF_TABLE[tf]["ms"])
    missing = sum(g[2] for g in gaps)
    expected = len(rows) + missing
    zero = sum(1 for r in rows if float(r[5]) == 0)
    st = {
        "n_rows": len(rows),
        "first": R.iso(int(rows[0][0])),
        "last": R.iso(int(rows[-1][0])),
        "n_gaps": len(gaps),
        "missing_candles": missing,
        "completeness_pct": round(100.0 * len(rows) / expected, 4) if expected else None,
        "n_zero_volume": zero,
        "gaps_sample": [{"after": R.iso(a), "before": R.iso(b), "missing": n}
                        for a, b, n in gaps[:10]],
    }
    if zero:
        st["warning_zero_volume"] = (
            "%d bougies sans aucune transaction : un backtest y remplira des "
            "ordres sur un marche qui n'existait pas." % zero)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--list", action="store_true", help="inventaire du repo")
    ap.add_argument("--asset", "--pair", dest="asset")
    ap.add_argument("--source", choices=["xperp", "perp"])
    ap.add_argument("--tf")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--format", choices=["ndjson", "json", "csv", "stats"],
                    default="ndjson")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    if args.list:
        for asset in R.list_assets(args.repo):
            print(asset)
            for source in R.list_sources(args.repo, asset):
                meta = R.read_source_meta(args.repo, asset, source) or {}
                tfs = meta.get("timeframes", {})
                print("  %-6s %-28s %d TF"
                      % (source, meta.get("instId", "?"), len(tfs)))
                for tf, t in tfs.items():
                    flag = ""
                    if t.get("missing_candles"):
                        flag = "  (%d manquantes)" % t["missing_candles"]
                    print("     %-5s %8d  %s -> %s%s"
                          % (tf, t["n_rows"], t["first"][:10], t["last"][:10], flag))
        return

    if not (args.asset and args.tf):
        sys.exit("--asset et --tf requis (ou --list)")

    source = resolve_source(args.repo, args.asset, args.source)
    rows = load(args.repo, args.asset, source, args.tf, args.start, args.end)
    fh = open(args.out, "w", newline="") if args.out else sys.stdout

    if args.format == "stats":
        st = stats(rows, args.tf)
        st["source"] = source
        json.dump(st, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    elif args.format == "json":
        json.dump([dict(zip(R.COLUMNS, r)) for r in rows], fh, ensure_ascii=False)
        fh.write("\n")
    elif args.format == "csv":
        w = csv.writer(fh)
        w.writerow(R.COLUMNS + ["datetime_utc"])
        for r in rows:
            w.writerow(r + [R.iso(int(r[0]))])
    else:
        for r in rows:
            fh.write(json.dumps(r, separators=(",", ":")) + "\n")

    if args.out:
        fh.close()
        print("%d bougies (%s) -> %s" % (len(rows), source, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
