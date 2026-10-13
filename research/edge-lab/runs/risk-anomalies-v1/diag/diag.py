"""Diagnostics DESCRIPTIFS post-run pour risk-anomalies-v1 (hors gates, ne changent pas le verdict)."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/mnt/skills/plugins/crypto-edge-lab/scripts")
import lab_engine as L

D = "/home/claude/edge-lab/risk-anomalies-v1"
spec = {**L.DEFAULTS, **json.load(open(f"{D}/spec.json"))}
panel = L.load_panel(spec, "/home/claude/jmarvillier/crypto-candles")
sig = L.compute_signal(L.load_signal(f"{D}/signal.py"), panel, spec)
T = L.build_targets(panel, spec)
alts = [a for a in panel if a != "BTC"]
H = 10
F = {f: L.pivot(sig, f, alts) for f in ["beta_btc_90", "idio_vol_30", "max_ret_30"]}
F["vol_30"] = pd.DataFrame({a: np.log(panel[a]["close"]).diff().rolling(30).std() for a in alts})
Y = L.pivot(T, f"res_{H}", alts)
lb = L.pivot(T, "listing_bar", alts)
ok = lb >= spec["min_listing_bars"]
for f in F: F[f] = F[f].where(ok)
Y = Y.where(ok)
btc = panel["BTC"]["close"]; btcf = np.log(btc.shift(-H) / btc)
first = {a: panel[a].index[0] for a in alts}

def ic_series(X, Yy, cols=None):
    X = X if cols is None else X[cols]; Yy = Yy if cols is None else Yy[cols]
    return L.row_spearman(X, Yy, spec["min_cross_section"])[0]

def summ(s, a="2024-07-01", b="2026-12-31"):
    s = s.loc[a:b].dropna(); return f"IC {s.mean():+.4f}  t {L.nw_t(s.values, H)[0]:+.2f}  n {len(s)}"

out = []
# 1) corrélations moyennes de rang entre features (cross-section)
names = list(F)
C = pd.DataFrame(index=names, columns=names, dtype=float)
for i in names:
    for j in names:
        C.loc[i, j] = ic_series(F[i], F[j]).mean()
print("== corrélation de rang moyenne (cross-section)\n", C.round(2))

# 2) IC partiel : rang de la feature résidualisé du rang de vol_30, date par date
def partial(X, Z):
    rx, rz = X.rank(axis=1), Z.rank(axis=1)
    res = rx.copy() * np.nan
    for d in rx.index:
        m = rx.loc[d].notna() & rz.loc[d].notna()
        if m.sum() < spec["min_cross_section"]: continue
        x, z = rx.loc[d, m], rz.loc[d, m]
        b = np.polyfit(z, x, 1); res.loc[d, m.index[m]] = x - np.polyval(b, z)
    return res
print(f"\n== h={H} j, OOS | IC brut vs IC partiel (vol_30 retirée)")
P = {}
for f in ["beta_btc_90", "idio_vol_30", "max_ret_30"]:
    P[f] = partial(F[f], F["vol_30"])
    print(f"{f:12s} brut: {summ(ic_series(F[f], Y))} | partiel: {summ(ic_series(P[f], Y))} | partiel IS: {summ(ic_series(P[f], Y), '2021-01-01', '2024-06-30')}")
print(f"{'vol_30':12s} brut: {summ(ic_series(F['vol_30'], Y))}")
pi = partial(F["vol_30"], F["idio_vol_30"])
print(f"{'vol_30|idio':12s} partiel: {summ(ic_series(pi, Y))}")

# 3) Dépendance au sens de BTC (artefact de bêta mal estimé ?)
print(f"\n== OOS : IC selon le signe du rendement BTC à {H} j")
for f in F:
    s = ic_series(F[f], Y).loc["2024-07-01":]
    up = s[btcf.reindex(s.index) > 0]; dn = s[btcf.reindex(s.index) <= 0]
    print(f"{f:12s} BTC↑ {up.mean():+.4f} (n {up.notna().sum()})   BTC↓ {dn.mean():+.4f} (n {dn.notna().sum()})")

# 4) Sans les actifs listés après 2022 (effet « dump post-listing »)
old = [a for a in alts if first[a] < pd.Timestamp("2023-01-01")]
print(f"\n== OOS, {len(old)} alts listées avant 2023 seulement (exclues : {sorted(set(alts)-set(old))})")
for f in F:
    print(f"{f:12s} {summ(ic_series(F[f], Y, old))}")

# 5) Spread Q5-Q1 par année (moyenne des rendements résiduels, h=10, sens attendu = Q1-Q5)
print(f"\n== Q1−Q5 (bas score − haut score) rendement résiduel moyen à {H} j, par année")
rows = []
for f in F:
    r = F[f].rank(axis=1, pct=True)
    q1 = Y.where(r <= 0.2).mean(axis=1); q5 = Y.where(r > 0.8).mean(axis=1)
    sp = (q1 - q5)
    yr = sp.groupby(sp.index.year).mean()
    rows.append(yr.rename(f))
print((pd.concat(rows, axis=1) * 100).round(2).T.to_string())
