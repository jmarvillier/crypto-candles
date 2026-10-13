"""season-v1 — effets calendaires daily (barres 1Dutc, index = open time UTC).
Événement en t = position prise à la CLÔTURE de la barre t ; le calendrier est connu à l'avance
(aucune donnée de prix utilisée, donc aucun look-ahead possible)."""
import numpy as np
import pandas as pd


def compute(df, ctx):
    idx = df.index
    # Lundi : barre du dimanche (weekday 6) -> on détient le lundi
    mon_long = np.where(idx.weekday == 6, 1, 0)
    # Turn-of-month : barre de l'avant-dernier jour du mois -> on détient
    # dernier jour + jours 1, 2, 3 du mois suivant (h = 4)
    tom_long = np.where((idx + pd.Timedelta(days=2)).day == 1, 1, 0)
    # Week-end : barre du vendredi (weekday 4) -> short samedi + dimanche (h = 2)
    wkend_short = np.where(idx.weekday == 4, -1, 0)
    return pd.DataFrame({"mon_long": mon_long, "tom_long": tom_long,
                         "wkend_short": wkend_short}, index=idx)
