"""Diagnostic post-hoc : même portefeuille quintile (sans couverture ni coûts), rendement hebdo
mesuré en LOG (comme le lab) vs SIMPLE (ce que gagne une position). Hors gates."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bt
C, V = bt.load_panel(); vol30, beta, elig = bt.features(C, V)
sun = [d for d in C.loc[bt.START:bt.END].index if d.dayofweek == 6]
rows = []
for d, n in zip(sun[:-1], sun[1:]):
    v = vol30.loc[d][elig.loc[d]].dropna().sort_values(); k = max(3, round(len(v) / 5))
    lo, hi = v.index[:k], v.index[-k:]
    s = C.loc[n] / C.loc[d] - 1; l = np.log(C.loc[n] / C.loc[d])
    rows.append({"date": n, "simple_LmH": s[lo].mean() - s[hi].mean(), "log_LmH": l[lo].mean() - l[hi].mean(),
                 "simple_hi": s[hi].mean(), "log_hi": l[hi].mean()})
D = pd.DataFrame(rows).set_index("date")
out = D.groupby(D.index.year).mean().mul(1e4).round(0)
out.loc["toutes"] = D.mean().mul(1e4).round(0)
print("moyennes hebdo en bps (L-H = long low-vol moins high-vol)"); print(out.to_string())
print("t (iid) :", {c: round(D[c].mean() / D[c].std() * len(D) ** .5, 2) for c in D})
out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "log_vs_simple.csv"))
