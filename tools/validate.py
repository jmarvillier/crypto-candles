#!/usr/bin/env python3
"""Controle d'integrite du repo. A lancer AVANT chaque commit.

Verifie par actif, par source et par TF : coherence OHLC, doublons, ordre,
arite, alignement sur la grille du TF, placement dans le bon shard, trous, et
homogeneite de la source (aucune bougie etrangere ne doit s'etre glissee dans
une arborescence).

Code retour 1 si une erreur bloquante est trouvee. Les trous ne sont PAS
bloquants : ils sont normaux et documentes.

    python validate.py --repo .
    python validate.py --repo . --asset BTC --strict
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ohlcv_repo as R          # noqa: E402


def validate_source(repo, asset, source, strict=False):
    errors, warnings = [], []
    expected_src = R.SOURCES[source]
    print("  --- %s ---" % source)
    for tf in R.ALL_TFS:
        if not os.path.isdir(R.tf_dir(repo, asset, source, tf)):
            continue
        rows = R.read_range(repo, asset, source, tf)
        if not rows:
            warnings.append("%s/%s/%s : repertoire vide" % (asset, source, tf))
            continue

        errs = R.check_rows(rows)

        # une arborescence de source ne doit contenir que sa propre source
        # (les TF derives portent "d", c'est legitime)
        intrus = {r[7] for r in rows} - {expected_src, "d"}
        if intrus:
            errs.append("bougies d'une autre source dans %s : %s"
                        % (source, ", ".join(sorted(intrus))))

        step = R.TF_TABLE[tf]["ms"]
        if step:
            off = R.grid_offset(tf)
            mis = [r for r in rows if int(r[0]) % step != off]
            if mis:
                errs.append("%d bougies non alignees sur la grille %s (ex: %s)"
                            % (len(mis), tf, R.iso(int(mis[0][0]))))

        for r in rows[:1] + rows[-1:]:
            exp = R.shard_path(repo, asset, source, tf, int(r[0]))
            if not os.path.exists(exp):
                errs.append("bougie %s absente du shard attendu %s"
                            % (R.iso(int(r[0])), os.path.relpath(exp, repo)))

        gaps = R.find_gaps(rows, step)
        missing = sum(g[2] for g in gaps)
        zero = sum(1 for r in rows if float(r[5]) == 0)

        status = "ERREUR" if errs else ("trous" if gaps else "ok")
        print("    %-5s %8d bougies  %s -> %s  [%s]"
              % (tf, len(rows), R.iso(int(rows[0][0]))[:10],
                 R.iso(int(rows[-1][0]))[:10], status))
        if gaps:
            pct = 100.0 * missing / (len(rows) + missing)
            msg = ("%s/%s/%s : %d trous, %d bougies manquantes (%.2f%%)"
                   % (asset, source, tf, len(gaps), missing, pct))
            print("          %s ; premier apres %s" % (msg, R.iso(gaps[0][0])))
            (errors if strict else warnings).append(msg)
        if zero:
            warnings.append("%s/%s/%s : %d bougies a volume nul (ex: %s)"
                            % (asset, source, tf, zero,
                               R.iso(int(next(r[0] for r in rows if float(r[5]) == 0)))))
        for e in errs[:5]:
            print("          ERREUR %s" % e)
            errors.append("%s/%s/%s : %s" % (asset, source, tf, e))

    if not R.read_source_meta(repo, asset, source):
        warnings.append("%s/%s : _meta.json absent (relancer sync_pair.py)"
                        % (asset, source))
    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--asset", "--pair", dest="asset", default="all")
    ap.add_argument("--strict", action="store_true",
                    help="traite les trous comme des erreurs bloquantes")
    args = ap.parse_args()

    assets = R.list_assets(args.repo) if args.asset == "all" else [args.asset.upper()]
    if not assets:
        sys.exit("aucun actif dans %s/data" % args.repo)

    all_err, all_warn = [], []
    for a in assets:
        print("\n=== %s ===" % a)
        for s in R.list_sources(args.repo, a):
            e, w = validate_source(args.repo, a, s, args.strict)
            all_err += e
            all_warn += w

    print("\n" + "-" * 62)
    print("%d actif(s) | %d erreur(s) | %d avertissement(s)"
          % (len(assets), len(all_err), len(all_warn)))
    for w in all_warn[:20]:
        print("  ATTENTION %s" % w)
    for e in all_err[:20]:
        print("  ERREUR    %s" % e)
    sys.exit(1 if all_err else 0)


if __name__ == "__main__":
    main()
