#!/usr/bin/env python3
"""Synchronise un actif du repo OHLCV depuis OKX.

Les deux sources sont stockees SEPAREMENT (data/<ACTIF>/xperp/ et
data/<ACTIF>/perp/) : chacune est une serie homogene, directement backtestable,
sans saut de prix artificiel.

  init     : cree l'arborescence et tire tout l'historique disponible.
  update   : ne tire que ce qui manque depuis la derniere bougie stockee.
  backfill : etend l'historique VERS LE PASSE, en s'arretant a la premiere
             bougie deja stockee. Ne refetche jamais l'existant.

Exemples
    python sync_pair.py --repo . --asset BTC --mode init
    python sync_pair.py --repo . --asset BTC --mode init --source perp --since 2020-01-01
    python sync_pair.py --repo . --asset all --mode update
    python sync_pair.py --repo . --asset BTC --source perp --mode backfill --since 2024-01-01
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ohlcv_repo as R          # noqa: E402
import okx_client as OKX        # noqa: E402

# Profondeur par defaut si --since n'est pas fourni. Le 1min complet depuis 2020
# represente ~3,4 M bougies et ~25 min d'API pour un seul actif : on ne le fait
# que sur demande explicite.
DEFAULT_SINCE = {"1min": "2024-01-01", "5min": "2022-01-01"}


def log(msg):
    print(msg, flush=True)


def _windows(since, until, shard):
    """Decoupe [since, until[ en fenetres de fetch.

    Mensuelles pour le 1min (un shard = un mois, donc une fenetre = un fichier
    ecrit), annuelles sinon. Une seule fenetre pour les TF a fichier unique :
    les volumes y sont derisoires.
    """
    if shard == "single":
        return [(since, until)]
    from datetime import datetime, timezone
    out = []
    d = datetime.fromtimestamp(since / 1000, timezone.utc)
    y, m = d.year, (d.month if shard == "month" else 1)
    cur = since
    while cur < until:
        if shard == "month":
            ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        else:
            ny, nm = y + 1, 1
        nxt = int(datetime(ny, nm, 1, tzinfo=timezone.utc).timestamp() * 1000)
        out.append((cur, min(nxt, until)))
        cur, y, m = nxt, ny, nm
    return out


def load_registry(repo):
    path = os.path.join(repo, "meta", "instruments.json")
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {}


def save_registry(repo, reg):
    path = os.path.join(repo, "meta", "instruments.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(reg, fh, indent=2, sort_keys=True)
        fh.write("\n")


def sync_tf(repo, asset, source, inst_id, tf, mode, since_arg):
    cfg = R.TF_TABLE[tf]
    if not cfg["bar"]:
        return 0

    step = cfg["ms"]
    until = None

    if mode == "update":
        stored = R.cutoff(repo, asset, source, tf)
        if stored is None:
            log("    %-5s aucune donnee -> lancer --mode init" % tf)
            return 0
        since = stored + (step or 1)
    elif mode == "backfill":
        since = R.to_ms(since_arg)
        if since is None:
            log("    %-5s --since obligatoire en backfill" % tf)
            return 0
        until = R.earliest(repo, asset, source, tf)
        if until is None:
            log("    %-5s aucune donnee -> comportement init" % tf)
        elif until <= since:
            log("    %-5s deja couvert depuis %s" % (tf, R.iso(until)[:10]))
            return 0
    else:
        since = R.to_ms(since_arg or DEFAULT_SINCE.get(tf))

    # Fetch par fenetres, avec ecriture apres chacune. Sans cela, un 1min sur un
    # an garde 500 000 bougies en memoire pendant 15 min et perd tout sur la
    # moindre coupure. En backfill on parcourt du plus recent au plus ancien :
    # `earliest()` descend au fur et a mesure, donc relancer la commande reprend
    # ou elle s'est arretee au lieu de tout refaire.
    windows = _windows(since, until or R.now_ms(), cfg["shard"])
    total_added = 0
    first_ts = last_ts = None
    n_rows = 0
    for w_since, w_until in reversed(windows):
        rows = OKX.fetch_candles(inst_id, cfg["bar"], since_ms=w_since,
                                 until_ms=w_until, src=R.SOURCES[source])
        if not rows:
            continue
        added, _skipped, _ = R.merge_rows(repo, asset, source, tf, rows)
        total_added += added
        n_rows += len(rows)
        first_ts = rows[0][0] if first_ts is None else min(first_ts, rows[0][0])
        last_ts = rows[-1][0] if last_ts is None else max(last_ts, rows[-1][0])
        if len(windows) > 1:
            log("      %-5s %s : %6d bougies, +%d" %
                (tf, R.iso(w_since)[:7], len(rows), added))

    if not n_rows:
        log("    %-5s a jour" % tf)
        return 0
    log("    %-5s %6d bougies (%s -> %s) +%d nouvelles" %
        (tf, n_rows, R.iso(first_ts)[:10], R.iso(last_ts)[:10], total_added))
    return total_added


def derive_tf(repo, asset, source, tf):
    cfg = R.TF_TABLE[tf]
    rows = R.read_range(repo, asset, source, cfg["derived_from"])
    if not rows:
        return 0
    agg = R.aggregate_calendar(rows, unit="year" if tf == "1y" else "month")
    n = R.write_shard(R.shard_path(repo, asset, source, tf, agg[0][0]), agg)
    log("    %-5s derive de %s : %d bougies" % (tf, cfg["derived_from"], n))
    return n


def sync_source(repo, asset, source, inst_id, mode, tfs, since_arg):
    log("  --- source %s (%s) ---" % (source, inst_id))
    for tf in tfs:
        if tf in R.NATIVE_TFS:
            sync_tf(repo, asset, source, inst_id, tf, mode, since_arg)
    for tf in tfs:
        if tf in R.DERIVED_TFS:
            # a re-deriver apres tout ajout, y compris un backfill qui rallonge
            # la serie source par le debut
            derive_tf(repo, asset, source, tf)
    meta = R.write_source_meta(repo, asset, source, extra={"instId": inst_id})
    log("      %d TF, %d bougies" %
        (len(meta["timeframes"]), sum(t["n_rows"] for t in meta["timeframes"].values())))


def sync_asset(repo, asset, mode, sources, tfs, since_arg):
    log("\n=== %s (%s) ===" % (asset.upper(), mode))
    reg = load_registry(repo)
    inst = reg.get(asset.upper())
    if inst is None or mode == "init":
        inst = OKX.resolve_instruments(asset)
        if not inst["xperp"] and not inst["swap"]:
            log("  ABANDON : aucun instrument OKX pour %s" % asset.upper())
            return False
        reg[asset.upper()] = inst
        save_registry(repo, reg)

    mapping = {"xperp": inst.get("xperp"), "perp": inst.get("swap")}
    done = False
    for source in sources:
        inst_id = mapping.get(source)
        if not inst_id:
            log("  source %s indisponible pour %s" % (source, asset.upper()))
            continue
        sync_source(repo, asset, source, inst_id, mode, tfs, since_arg)
        done = True
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--asset", "--pair", dest="asset", required=True,
                    help="BTC, ou 'all' pour tout le repo")
    ap.add_argument("--mode", choices=["init", "update", "backfill"],
                    default="update")
    ap.add_argument("--source", default="all",
                    choices=["all", "xperp", "perp"],
                    help="quelle serie alimenter (defaut : les deux)")
    ap.add_argument("--tf", default="all", help="liste separee par des virgules, ou 'all'")
    ap.add_argument("--since", default=None,
                    help="borne basse (YYYY-MM-DD). Defaut : tout l'historique "
                         "sauf 1min (2024-01) et 5min (2022-01).")
    args = ap.parse_args()

    tfs = R.ALL_TFS if args.tf == "all" else [t.strip() for t in args.tf.split(",")]
    bad = [t for t in tfs if t not in R.TF_TABLE]
    if bad:
        sys.exit("TF inconnus : %s (connus : %s)" % (bad, ", ".join(R.ALL_TFS)))

    sources = list(R.SOURCES) if args.source == "all" else [args.source]
    assets = R.list_assets(args.repo) if args.asset == "all" else [args.asset.upper()]
    if not assets:
        sys.exit("repo vide : lancer init_repo.py puis --mode init sur un actif")

    ok = sum(1 for a in assets
             if sync_asset(args.repo, a, args.mode, sources, tfs, args.since))
    log("\n%d/%d actifs synchronises." % (ok, len(assets)))


if __name__ == "__main__":
    main()
