# risk-anomalies-v1 — pré-enregistrement
Figé le 2026-10-13, AVANT le premier run. Contrôle look-ahead passé (40 actifs).
Statut : GO de Jérémie reçu le 2026-10-13 avant tout run (protocole inchangé).

## Hypothèse
- Les alts « loterie » / à risque élevé sous-performent BTC×β ensuite (anomalies de risque : betting-against-beta, vol idiosyncratique, MAX).
- Mécanisme : demande de levier et de profils à queue droite (traders contraints / particuliers) qui surpaie ces actifs ; l'edge est payé par les acheteurs de loterie.
- Falsification : IC OOS ≥ 0 ou non significatif, ou signe instable par année.
- Lien avec l'existant : vol_30 (vol TOTALE) a été GO dans le factor lab du 12/10. Ici on teste si l'effet vient du bêta, de l'idiosyncratique ou des queues — trois mécanismes distincts.

## Signal (feature, daily)
- beta_btc_90 : β glissant 90 j des log-rendements vs BTC (min 60 obs).
- idio_vol_30 : écart-type 30 j du résidu r − β90·r_BTC.
- max_ret_30 : plus forte hausse journalière (log) des 30 derniers jours.
- Sens attendu : −1 pour les trois.

## Données et fenêtres
- perp 1d, 40 actifs (BTC = référence, exclu de l'IC). IS 2021-01-01 → 2024-06-30 ; OOS 2024-07-01 → aujourd'hui.

## Tests
- XS uniquement (anomalies de section), cible res (alt vs BTC×β 90 j), h = 5, 10, 20 j. Coût 0,15 %/jambe.

## Gates — défaut methodology §3 (G1–G7), BH sur les 9 tests du run.

## Suite
CANDIDAT → backtest long-short pré-enregistré (crypto-backtest-forge), funding des shorts compris, puis contrôle xperp. PISTE → une v2 max. REJETÉ → clôture.
