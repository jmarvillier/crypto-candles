# btc-leadlag-v1 — pré-enregistrement
Figé le 2026-10-13, AVANT le premier run. Contrôle look-ahead passé (40 actifs).
Statut : GO de Jérémie reçu le 2026-10-13 avant tout run (protocole inchangé).

## Hypothèse
- Les alts intègrent les mouvements de BTC avec retard : une alt « en retard » sur BTC sur 1–3 h rattrape ensuite.
- Mécanisme : diffusion lente de l'information du marché directeur vers les carnets moins liquides (lead-lag documenté sur actions et crypto). Payé par les teneurs de marché lents à réajuster.
- Falsification : IC OOS ≤ 0 ou non significatif ; ou effet réel mais sous le plancher de coûts (attendu probable vu l'historique intraday — on le mesure quand même pour fermer la question).

## Signal (feature, 1h)
- gap_btc_kh = β30j(décalé 1 barre) × r_BTC(k h) − r_alt(k h), k = 1 et 3.
- Sens attendu : +1.

## Données et fenêtres
- perp 1h, 40 actifs. IS 2021-01-01 → 2024-06-30 ; OOS 2024-07-01 → aujourd'hui.

## Tests
- XS, cible res (β 720 barres), h = 1, 2, 4 h. Coût 0,15 %/jambe.

## Gates — défaut methodology §3, BH sur les 6 tests du run.

## Suite
Même règle. Rappel : un CANDIDAT intraday doit en plus passer le test frais maker vs taker en backtest.
