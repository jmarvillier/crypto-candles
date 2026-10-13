"""btc-leadlag-v1 — 1h. Écart de rattrapage : ce que l'alt « aurait dû » faire vu BTC
sur les k dernières heures, moins ce qu'elle a fait. Positif = alt en retard sur une hausse BTC."""
import numpy as np
import pandas as pd


def compute(df, ctx):
    r = np.log(df["close"]).diff()
    rb = np.log(ctx["btc"]["close"].reindex(df.index)).diff()
    # beta 30 j en barres horaires, décalé d'une barre (pas de chevauchement avec la fenêtre du gap)
    beta = (r.rolling(720, min_periods=480).cov(rb) / rb.rolling(720, min_periods=480).var()).shift(1)
    out = {}
    for k in (1, 3):
        out[f"gap_btc_{k}h"] = beta * rb.rolling(k).sum() - r.rolling(k).sum()
    return pd.DataFrame(out, index=df.index)
