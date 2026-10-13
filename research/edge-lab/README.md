# edge-lab — registre de recherche

Résultats du skill **crypto-edge-lab**, séparés des données (`data/`). Rien ici n'est lu par
les outils du repo ; `tools/validate.py` ne contrôle que `data/`.

## Contenu

```
ledger.csv                 registre cumulatif : une ligne par test lancé (feature × test × h)
runs/<nom>/PREREG.md       pré-enregistrement figé AVANT le run
runs/<nom>/spec.json       paramètres du run
runs/<nom>/signal.py       définition exacte du signal
runs/<nom>/DATA_SHA        commit de crypto-candles utilisé
runs/<nom>/out/            tests.csv, annees.csv, checks.json, meta.json, Excel
runs/<nom>/diag/           contrôles descriptifs post-run (hors gates, ne changent pas le verdict)
```

Pour les prochains runs, pointer `"ledger"` de la spec vers ce fichier
(`<clone>/research/edge-lab/ledger.csv`) puis committer. Dans les spec.json archivées, seul le
chemin du registre a été réécrit après coup ; le protocole est inchangé.

## Tests antérieurs au registre (non listés ligne à ligne)

- Factor lab du 12/10/2026 : 12 features daily, 3 horizons → 1 GO (`vol_30` en rang, h7/h30).
- Factor lab v1 du 13/10/2026 : 72 tests (13 features + audit du score du scanner) → 0 CANDIDAT,
  retournement résiduel 1 j en PISTE.

Total approximatif avant ce registre : ~90 tests. À ajouter au décompte avant d'interpréter un
CANDIDAT isolé.

## Journal des runs

| date | run | tests | verdict | conclusion |
|---|---|---|---|---|
| 2026-10-13 | risk-anomalies-v1 | 9 | 9 CANDIDAT | Redondant avec `vol_30` (corr. de rang 0,49 / 0,89 / 0,81). Une fois vol_30 retirée, aucun IC partiel stable IS+OOS. Le bêta est suspect (IC −0,16 quand BTC monte, −0,05 quand il baisse). Confirme la low-vol des alts : tient sans les listings post-2022, quel que soit le sens de BTC. Spread inversé en 2021 (saison des alts), faible en 2026. |
| 2026-10-13 | btc-leadlag-v1 | 6 | 6 PISTE | Information réelle (IC OOS +0,025 à +0,03, t 14–19) mais ≈ 1 bp/h de spread contre ~30 bps de coût. IC divisé par 3 depuis 2021. **Clos.** |
| 2026-10-13 | backtest lowvol-ls-v1 (hors registre, `research/backtest/`) | 1 backtest, 7 gates | NO-GO 0/7 | Long low-vol / short high-vol couvert bêta : −19 %/an, Sharpe −0,21, 2021 −81 %, négatif avant coûts. Spread hebdo +61 bps en log mais −61 bps en simple : l'edge du lab venait de la cible log (traînée de volatilité) et du piège rang ≠ moyenne. Piste low-vol **close** ; CANDIDAT de risk-anomalies-v1 non confirmés (même biais). |

## Suite ouverte

Aucune piste de backtest ouverte. Correctif du moteur edge-lab à faire avant tout nouveau run :
calculer spread Q5−Q1 et gate « net de coûts » (G7) en rendement SIMPLE, garder l'IC de rang
pour le pouvoir prédictif (cf. research/backtest/lowvol-ls-v1/RESULTATS.md).
