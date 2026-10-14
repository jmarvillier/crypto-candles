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
| 2026-10-13 | season-v1 | 9 | 9 REJETÉ | Saisonnalités calendaires daily, 40 perps, cible brute. Lundi long : nul (OOS +2 bps, p_perm 0,54). Turn-of-month long : très bon en IS (+1,9 % sur 4 j) mais négatif en OOS (−0,45 % à −1,45 %), 27 dates OOS seulement (t NW non calculable). Week-end short : le samedi monte plutôt (−41 bps pour le short, p_perm 1,0) ; seul h4 bat le hasard (p 0,005) pour 6 bps net, t 0,3 : bruit. Famille « saisonnalité daily » **close** ; une version intraday 1h buterait sur le plancher de coûts. |
| 2026-10-14 | wm-neckline-v1 | 6 | 6 REJETÉ | Figures W / M daily mécaniques (pivots K=5, creux/sommets à ±3 %, hauteur ≥ 5 %, cassure du cou en clôture), 40 perps, cible brute, h 5/10/20. **W long** : fort en IS et meilleur que le hasard (h20 +20,7 %, p_perm 0,005, porté par 2021 +49 %) mais effondré en OOS (h20 +2,0 % vs +0,5 % au hasard, p_perm 0,29 ; 2025 négatif). **M short** : du mauvais côté en IS comme en OOS (h10 −2,7 %, h20 −3,2 %) — après un M cassé le prix a plutôt monté, sans que ce soit significatif. Échantillon mince (~60 événements par période, ~45 dates). Famille « doubles creux / sommets daily » **close** : pas d'appui pour une grille directionnelle. |

## Moteur 1.2 (2026-10-13) et relecture des verdicts antérieurs

Le moteur ≤ 1.1 mesurait spread, net de coûts et années en rendement LOG et ne jugeait le net
qu'en OOS. Depuis 1.2 : spread / G6 / G7 / événements en rendement simple, G7 en IS ET OOS,
G6 sur le spread simple annuel. Relecture DESCRIPTIVE (registre inchangé, aucune ligne ajoutée) :
- vol_30 (h 5/10/20) : CANDIDAT → **PISTE** (cohérent avec le NO-GO du backtest lowvol-ls-v1) ;
- risk-anomalies-v1 : idio_vol_30 et max_ret_30 → **PISTE** ; beta_btc_90 reste CANDIDAT
  (spread simple du bon signe en IS et OOS, 4/6 années) — à lire avec ~105 tests au total et sa
  redondance partielle avec vol_30 ;
- btc-leadlag-v1 : inchangé (PISTE).

## Suite ouverte

Aucune piste de backtest ouverte. Seul CANDIDAT survivant au moteur 1.2 : beta_btc_90 (faible
conviction, cf. ci-dessus). Tout nouveau run se fait avec le moteur ≥ 1.2.
Familles closes sur OHLCV : tendance/momentum, retournement, volatilité/bêta/MAX, lead-lag BTC,
saisonnalité daily, figures W/M daily. Familles proposées non lancées : retournement 1 j conditionné au volume
(Campbell-Grossman-Wang), ancrage au plus haut 365 j. Décompte : ~120 tests (30 au registre +
~90 antérieurs).
