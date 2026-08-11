#!/usr/bin/env python3
"""Mesure l'ecart entre les deux series d'un meme actif sur leur recouvrement.

A quoi ca sert : un edge valide sur `perp` (historique profond) sera exploite
sur `xperp` (instrument reellement trade). Ce script chiffre a quel point les
deux instruments se ressemblent — donc a quel point le transfert est credible.

Ce qu'il faut regarder :
  basis_median_bps   ecart de prix systematique. Un biais constant deplace tous
                     les niveaux absolus : stops fixes, grilles, breakouts.
  basis_std_bps      instabilite de l'ecart. C'est le vrai risque : un basis
                     constant se corrige, un basis erratique non.
  corr_returns       correlation des rendements. Proche de 1 => la dynamique se
                     transfere. En dessous de ~0,95, se mefier.
  vol_ratio          liquidite relative. Un xperp beaucoup plus fin implique un
                     slippage que le backtest sur perp n'a pas vu.

    python compare_sources.py --repo . --asset BTC --tf 1h
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ohlcv_repo as R          # noqa: E402


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def pearson(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return round(num / (da * db), 6) if da and db else None


def compare(repo, asset, tf):
    x = {int(r[0]): r for r in R.read_range(repo, asset, "xperp", tf)}
    p = {int(r[0]): r for r in R.read_range(repo, asset, "perp", tf)}
    common = sorted(set(x) & set(p))
    if len(common) < 10:
        return {"error": "recouvrement insuffisant (%d bougies communes)" % len(common)}

    bps = []
    for ts in common:
        cx, cp = float(x[ts][4]), float(p[ts][4])
        if cp:
            bps.append((cx - cp) / cp * 10_000)
    mean_bps = sum(bps) / len(bps)
    var = sum((b - mean_bps) ** 2 for b in bps) / len(bps)

    rx, rp = [], []
    for a, b in zip(common, common[1:]):
        ox, op = float(x[a][4]), float(p[a][4])
        if ox and op:
            rx.append(float(x[b][4]) / ox - 1)
            rp.append(float(p[b][4]) / op - 1)

    vx = sum(float(x[ts][6]) for ts in common)
    vp = sum(float(p[ts][6]) for ts in common)

    return {
        "asset": asset.upper(), "tf": tf,
        "overlap_candles": len(common),
        "overlap_from": R.iso(common[0]), "overlap_to": R.iso(common[-1]),
        "basis_median_bps": round(median(bps), 2),
        "basis_mean_bps": round(mean_bps, 2),
        "basis_std_bps": round(var ** 0.5, 2),
        "basis_min_bps": round(min(bps), 2),
        "basis_max_bps": round(max(bps), 2),
        "corr_returns": pearson(rx, rp),
        "vol_quote_xperp": round(vx, 2),
        "vol_quote_perp": round(vp, 2),
        "vol_ratio_xperp_over_perp": round(vx / vp, 4) if vp else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--asset", "--pair", dest="asset", required=True)
    ap.add_argument("--tf", default="1h")
    args = ap.parse_args()
    print(json.dumps(compare(args.repo, args.asset, args.tf),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
