"""lowvol-ls-v1 — backtest long/short low-vol des alts, couvert en bêta BTC.
Protocole : PREREG.md (figé avant run). Usage :
  python bt.py --check-only   # contrôle look-ahead + couverture, aucun rendement calculé
  python bt.py                # run complet -> out/
"""
import json, os, sys, argparse
import numpy as np
import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(os.path.dirname(__file__), "out")
START, IS_END, OOS_START, END = "2021-01-04", "2024-06-30", "2024-07-01", "2026-10-12"
MIN_LIST, VOL_N, BETA_N = 120, 30, 90
C_ALT, C_BTC = 0.0005 + 0.0005, 0.0005 + 0.0002
F_STRESS = 0.11  # funding annuel payé par la jambe short (scénario STRESS)


def load_panel():
    sys.path.insert(0, os.path.join(REPO, "tools"))
    from read_ohlcv import load
    meta = json.load(open(os.path.join(REPO, "meta", "instruments.json")))
    close, volq = {}, {}
    for a in sorted(meta):
        rows = load(REPO, a, "perp", "1d", "2019-01-01", "2026-10-14")
        df = pd.DataFrame([r[:7] for r in rows], columns=["ts", "o", "h", "l", "c", "vb", "vq"])
        df.index = pd.to_datetime(df["ts"], unit="ms")
        close[a], volq[a] = df["c"].astype(float), df["vq"].astype(float)
    C = pd.DataFrame(close).sort_index().loc[:END]
    V = pd.DataFrame(volq).reindex(C.index)
    return C, V


def features(C, V):
    """Tout est calculé avec des fenêtres glissantes sur le passé : valeur en t connue à la clôture de t."""
    r = np.log(C).diff()
    active = V > 0
    first = active.idxmax().where(active.any())
    age = pd.DataFrame({a: (C.index - first[a]).days for a in C}, index=C.index)
    vol30 = r.rolling(VOL_N, min_periods=20).std()
    rb = r["BTC"]
    beta = r.rolling(BETA_N, min_periods=60).cov(rb).div(rb.rolling(BETA_N, min_periods=60).var(), axis=0).clip(0, 3)
    live30 = active.rolling(30, min_periods=30).min() == 1
    elig = (age >= MIN_LIST) & live30 & vol30.notna() & beta.notna()
    elig["BTC"] = False
    return vol30, beta, elig


def targets(vol30, beta, elig, dates):
    W = {}
    for d in dates:
        e = elig.loc[d]
        v = vol30.loc[d][e].dropna()
        N = len(v)
        if N < 6:
            continue
        n = max(3, int(round(N / 5)))
        s = v.sort_values()
        w = pd.Series(0.0, index=vol30.columns)
        w[s.index[:n]] = 0.5 / n
        w[s.index[-n:]] = -0.5 / n
        w["BTC"] = -(w.drop("BTC") * beta.loc[d].fillna(0)).sum()
        W[d] = w
    return pd.DataFrame(W).T


def lookahead_check(C, V, n_cuts=8, seed=0):
    vol30, beta, elig = features(C, V)
    rng = np.random.default_rng(seed)
    idx = C.loc[START:].index
    bad = 0
    for cut in rng.choice(idx[:-30], n_cuts, replace=False):
        v2, b2, e2 = features(C.loc[:cut], V.loc[:cut])
        for full, part in ((vol30, v2), (beta, b2)):
            a, b = full.loc[cut], part.loc[cut]
            m = a.notna() & b.notna()
            bad += int((~np.isclose(a[m], b[m], rtol=1e-9, atol=1e-12)).sum())
        bad += int((elig.loc[cut] != e2.loc[cut]).sum())
    return bad


def nw_t(x, lag):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x)
    u = x - x.mean(); s = (u @ u) / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (u[k:] @ u[:-k]) / n
    return x.mean() / np.sqrt(s / n)


def stats(ret, label):
    eq = (1 + ret).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    yrs = len(ret) / 52
    return {"scenario": label, "semaines": len(ret), "rend_total_%": 100 * (eq.iloc[-1] - 1),
            "rend_annuel_%": 100 * (eq.iloc[-1] ** (1 / yrs) - 1), "vol_annuelle_%": 100 * ret.std() * np.sqrt(52),
            "sharpe": ret.mean() / ret.std() * np.sqrt(52), "t_NW4": nw_t(ret, 4), "maxDD_%": 100 * dd,
            "semaines_pos_%": 100 * (ret > 0).mean()}


def run(C, V):
    vol30, beta, elig = features(C, V)
    sundays = [d for d in C.loc[START:END].index if d.dayofweek == 6]
    W = targets(vol30, beta, elig, sundays)
    reb = list(W.index)
    rows = []
    prev = pd.Series(0.0, index=W.columns)
    for i, d in enumerate(reb[:-1]):
        nxt = reb[i + 1]
        w = W.loc[d]
        R = (C.loc[nxt] / C.loc[d] - 1).reindex(w.index).fillna(0.0)
        dw = (w - prev).abs()
        cost = dw.drop("BTC").sum() * C_ALT + dw["BTC"] * C_BTC
        alts = w.drop("BTC")
        gross = (w * R).sum()
        days = (nxt - d).days
        fund_stress = F_STRESS * 0.5 * days / 365
        dn = (alts * R.drop("BTC")).sum()  # dollar-neutre sans couverture
        rows.append({"date": nxt, "brut": gross, "cout": cost, "net": gross - cost, "net_stress": gross - cost - fund_stress,
                     "jambe_long": (alts.clip(lower=0) * R.drop("BTC")).sum(), "jambe_short": (alts.clip(upper=0) * R.drop("BTC")).sum(),
                     "couverture_btc": w["BTC"] * R["BTC"], "dollar_neutre_net": dn - dw.drop("BTC").sum() * C_ALT,
                     "n_jambe": int((alts > 0).sum()), "N_univers": int(elig.loc[d].sum()), "btc_hedge_w": w["BTC"],
                     "rotation": dw.sum(), "longs": " ".join(alts[alts > 0].index), "shorts": " ".join(alts[alts < 0].index)})
        prev = w
    return pd.DataFrame(rows).set_index("date")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check-only", action="store_true"); a = ap.parse_args()
    C, V = load_panel()
    bad = lookahead_check(C, V)
    _, _, elig = features(C, V)
    cov = elig.loc[START:].sum(axis=1)
    print(f"look-ahead : {bad} écart(s) ; univers éligible min/med/max = {cov.min()}/{int(cov.median())}/{cov.max()}")
    if bad:
        sys.exit(2)
    if a.check_only:
        return
    os.makedirs(OUT, exist_ok=True)
    df = run(C, V)
    df.to_csv(os.path.join(OUT, "semaines.csv"))
    S = []
    for lab, col, sl in [("BASE complet", "net", slice(None)), ("BASE IS", "net", slice(None, IS_END)),
                         ("BASE OOS", "net", slice(OOS_START, None)), ("STRESS funding", "net_stress", slice(None)),
                         ("brut (sans coûts)", "brut", slice(None)), ("diag dollar-neutre", "dollar_neutre_net", slice(None))]:
        S.append(stats(df.loc[sl, col], lab))
    S = pd.DataFrame(S)
    Y = df.groupby(df.index.year).agg(net=("net", lambda x: (1 + x).prod() - 1), stress=("net_stress", lambda x: (1 + x).prod() - 1),
                                       brut=("brut", lambda x: (1 + x).prod() - 1), jambe_long=("jambe_long", "sum"),
                                       jambe_short=("jambe_short", "sum"), couverture=("couverture_btc", "sum"),
                                       dollar_neutre=("dollar_neutre_net", lambda x: (1 + x).prod() - 1), semaines=("net", "size"))
    base, isr, oos, st = S.iloc[0], S.iloc[1], S.iloc[2], S.iloc[3]
    yrs = len(df) / 52
    be_fund = df["net"].mean() * 52 / 0.5  # taux annuel payé par la jambe short qui annule le net (approx. arithmétique)
    cost_share = df["cout"].sum() / df["brut"].sum() if df["brut"].sum() > 0 else np.inf
    y2021 = Y.loc[2021, "net"]
    G = {"G1 Sharpe>=0.5": base["sharpe"] >= 0.5, "G2 t_NW>=2": base["t_NW4"] >= 2.0,
         "G3 IS>0 et OOS>0": isr["rend_total_%"] > 0 and oos["rend_total_%"] > 0,
         "G4 annees>=4/6": int((Y["net"] > 0).sum()) >= 4,
         "G5 2021>=-15% et DD<=25%": y2021 >= -0.15 and base["maxDD_%"] >= -25,
         "G6 STRESS annuel>0": st["rend_annuel_%"] > 0, "G7 couts<50% brut": cost_share < 0.5}
    verdict = "GO in-sample" if all(G.values()) else "NO-GO"
    meta = {"verdict": verdict, "gates": {k: bool(v) for k, v in G.items()}, "annees_positives": int((Y["net"] > 0).sum()),
            "net_2021_%": 100 * y2021, "part_couts_%": 100 * cost_share, "funding_breakeven_annuel_%": 100 * be_fund,
            "rotation_hebdo_moy": df["rotation"].mean(), "data_sha": open(os.path.join(os.path.dirname(__file__), "DATA_SHA")).read().strip()}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=2, ensure_ascii=False)
    with pd.ExcelWriter(os.path.join(OUT, "lowvol-ls-v1.xlsx")) as xw:
        pd.DataFrame([{"gate": k, "ok": "OUI" if v else "NON"} for k, v in G.items()] + [{"gate": "VERDICT", "ok": verdict}]).to_excel(xw, "Verdict", index=False)
        S.round(3).to_excel(xw, "Synthèse", index=False)
        (Y.drop(columns="semaines") * 100).round(2).assign(semaines=Y["semaines"]).to_excel(xw, "Par année")
        q = df.groupby(df.index.to_period("Q")).agg(net=("net", lambda x: 100 * ((1 + x).prod() - 1)))
        q.index = q.index.astype(str); q.round(2).to_excel(xw, "Par trimestre")
        df.assign(equity_net=(1 + df["net"]).cumprod()).to_excel(xw, "Semaines")
        pd.DataFrame([meta]).drop(columns=["gates"]).T.to_excel(xw, "Méta", header=False)
    print(S.round(3).to_string(index=False)); print((Y.drop(columns="semaines") * 100).round(2).to_string()); print(json.dumps(meta, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
