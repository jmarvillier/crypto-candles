#!/usr/bin/env python3
"""Redecoupe les fichiers d'un repo selon la regle de sharding courante.

A lancer quand `TF_TABLE` change de decoupage (par ex. un TF qui passe de
fichier unique a sous-repertoires annuels). Lit toutes les bougies d'une serie,
les reecrit aux bons emplacements, puis supprime les fichiers devenus obsoletes.

Aucune bougie n'est perdue : le nombre de lignes est compare avant/apres et le
script s'arrete si l'egalite n'est pas verifiee.

    python reshard.py --repo . --dry-run
    python reshard.py --repo .
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ohlcv_repo as R          # noqa: E402


def reshard_tf(repo, asset, source, tf, dry_run):
    old_files = R.list_shards(repo, asset, source, tf)
    if not old_files:
        return 0, []
    rows = R.read_range(repo, asset, source, tf)
    if not rows:
        return 0, []

    wanted = {}
    for r in rows:
        wanted.setdefault(R.shard_path(repo, asset, source, tf, int(r[0])), []).append(r)

    stale = [f for f in old_files if f not in wanted]
    if not stale and set(old_files) == set(wanted):
        return 0, []

    print("  %s/%s/%s : %d bougies, %d fichier(s) -> %d"
          % (asset, source, tf, len(rows), len(old_files), len(wanted)))
    for f in sorted(wanted):
        print("      + %s" % os.path.relpath(f, repo))
    for f in sorted(stale):
        print("      - %s" % os.path.relpath(f, repo))
    if dry_run:
        return len(rows), stale

    written = 0
    for path, rs in wanted.items():
        written += R.write_shard(path, rs)
    if written != len(rows):
        sys.exit("ARRET : %d bougies ecrites pour %d lues sur %s/%s/%s"
                 % (written, len(rows), asset, source, tf))
    for f in stale:
        os.remove(f)
    # repertoires vides laisses par la migration
    for root, dirs, files in os.walk(R.tf_dir(repo, asset, source, tf), topdown=False):
        if not os.listdir(root):
            os.rmdir(root)
    return len(rows), stale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total, moved = 0, 0
    for asset in R.list_assets(args.repo):
        for source in R.list_sources(args.repo, asset):
            for tf in R.ALL_TFS:
                if not os.path.isdir(R.tf_dir(args.repo, asset, source, tf)):
                    continue
                n, stale = reshard_tf(args.repo, asset, source, tf, args.dry_run)
                total += n
                moved += len(stale)

    if not moved:
        print("Rien a redecouper : le repo respecte deja la regle courante.")
    else:
        print("\n%s : %d bougies redecoupees, %d fichier(s) obsolete(s)%s."
              % ("Simulation" if args.dry_run else "Termine", total, moved,
                 "" if args.dry_run else " supprime(s)"))
        if not args.dry_run:
            for asset in R.list_assets(args.repo):
                for source in R.list_sources(args.repo, asset):
                    R.write_source_meta(args.repo, asset, source)
            print("_meta.json regeneres.")


if __name__ == "__main__":
    main()
