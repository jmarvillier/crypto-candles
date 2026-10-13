"""risk-anomalies-v1 — 3 features daily, alts vs BTC (cible résiduelle).
Toutes calculables à la clôture de t (rolling sur le passé uniquement)."""
import numpy as np
import pandas as pd


def compute(df, ctx):
    c = df["close"]
    r = np.log(c).diff()
    rb = np.log(ctx["btc"]["close"].reindex(df.index)).diff()
    # beta glissant 90 j vs BTC
    cov = r.rolling(90, min_periods=60).cov(rb)
    var = rb.rolling(90, min_periods=60).var()
    beta = cov / var
    # vol idiosyncratique 30 j : écart-type du résidu r - beta*rb (beta figé 90 j, connu en t)
    resid = r - beta * rb
    idio = resid.rolling(30, min_periods=20).std()
    # MAX : plus forte hausse journalière sur 30 j
    mx = r.rolling(30, min_periods=20).max()
    return pd.DataFrame({"beta_btc_90": beta, "idio_vol_30": idio, "max_ret_30": mx}, index=df.index)
