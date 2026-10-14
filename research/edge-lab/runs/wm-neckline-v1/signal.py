"""wm-neckline-v1 — figures W (double creux) et M (double sommet), cassure de la ligne de cou.

Tout est causal : un pivot d'indice i n'est connu qu'à la clôture de la barre i+K (il faut K
barres à droite). Le scan avance barre par barre et n'utilise que des données <= t.

Paramètres figés :
  K        = 5     pivots fractals : plus bas (haut) strict des barres [i-K, i+K]
  GAP      = 10..60 barres entre les deux pivots
  TOL      = 3 %   écart max entre les deux creux (sommets)
  DEPTH    = 5 %   hauteur min de la figure : (cou - creux) / cou   [M : (sommet - cou) / cou]
  WAIT     = 30    barres max entre la confirmation du 2e pivot et la cassure
W : +1 à la 1re clôture > cou (cou = plus haut entre les deux creux), si aucune clôture sous
    le plus bas des deux creux depuis le 2e creux. Un événement par figure.
M : -1, miroir exact.
"""
import numpy as np
import pandas as pd

K, GAP_MIN, GAP_MAX, TOL, DEPTH, WAIT = 5, 10, 60, 0.03, 0.05, 30


def _pivots(x, kind):
    n = len(x); out = np.zeros(n, bool)
    for i in range(K, n - K):
        w = x[i - K:i + K + 1]
        if np.isnan(w).any():
            continue
        if kind == "low" and x[i] == w.min() and (w == x[i]).sum() == 1:
            out[i] = True
        if kind == "high" and x[i] == w.max() and (w == x[i]).sum() == 1:
            out[i] = True
    return out


def _scan(df, side):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(c); ev = np.zeros(n)
    piv = _pivots(l if side == "W" else h, "low" if side == "W" else "high")
    known = []          # pivots confirmés jusqu'ici (indices)
    used = set()        # 2e pivot déjà consommé par une figure
    for t in range(n):
        j = t - K       # pivot qui devient connu à la clôture de t
        if j >= 0 and piv[j]:
            known.append(j)
        if len(known) < 2:
            continue
        i2 = known[-1]; i1 = known[-2]
        if i2 in used or t - (i2 + K) > WAIT or not (GAP_MIN <= i2 - i1 <= GAP_MAX):
            continue
        if side == "W":
            p1, p2 = l[i1], l[i2]
            if abs(p2 / p1 - 1) > TOL:
                continue
            neck = h[i1:i2 + 1].max(); floor = min(p1, p2)
            if (neck - floor) / neck < DEPTH:
                continue
            if (c[i2:t] < floor).any():          # invalidée avant la cassure
                used.add(i2); continue
            if c[t] > neck and (c[i2 + 1:t] <= neck).all():
                ev[t] = 1; used.add(i2)
        else:
            p1, p2 = h[i1], h[i2]
            if abs(p2 / p1 - 1) > TOL:
                continue
            neck = l[i1:i2 + 1].min(); roof = max(p1, p2)
            if (roof - neck) / neck < DEPTH:
                continue
            if (c[i2:t] > roof).any():
                used.add(i2); continue
            if c[t] < neck and (c[i2 + 1:t] >= neck).all():
                ev[t] = -1; used.add(i2)
    return ev


def compute(df, ctx):
    return pd.DataFrame({"w_long": _scan(df, "W"), "m_short": _scan(df, "M")}, index=df.index)
