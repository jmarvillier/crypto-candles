# season-v1 — pré-enregistrement

Figé le 2026-10-13, AVANT le premier run (contrôle look-ahead passé, aucun résultat vu).
Toute modification après résultats = nouvelle version (season-v2) pré-déclarée, et les deux
runs comptent dans le registre.

GO utilisateur : 2026-10-13, avec ajout demandé d'un 3e événement (short du week-end) avant tout run ; horizons étendus à 1/2/4 en conséquence.

## Hypothèse
- Idée en une phrase : des saisonnalités calendaires (deux documentées en crypto et actions, une
  ajoutée) donnent un rendement directionnel au-delà de la dérive du marché.
  - **Effet lundi** (Caporale & Plastun 2019 sur BTC) : le lundi UTC surperforme.
  - **Turn-of-month** (Lakonishok & Smidt 1988 ; observé sur BTC dans plusieurs études) :
    le dernier jour du mois et les 3 premiers jours du suivant surperforment.
  - **Week-end** (ajout utilisateur) : samedi + dimanche UTC sous-performent.
- Mécanisme supposé :
  - lundi : liquidité mince le week-end, l'information s'accumule et les desks institutionnels
    / flux ETF spot US reprennent en début de semaine ; ceux qui paient sont les vendeurs de
    week-end qui fournissent la liquidité au mauvais moment ;
  - turn-of-month : flux d'entrée calendaires (salaires, DCA, plans d'investissement,
    rééquilibrages mensuels des fonds) concentrés autour du changement de mois ;
  - week-end : marchés traditionnels fermés, carnets plus minces, flux surtout retail ; le
    mécanisme directionnel est le plus faible des trois (la littérature montre surtout une
    vol plus basse le week-end, pas un signe stable). À lire avec ce scepticisme.
- Ce qui la falsifierait : rendement moyen OOS ≤ 0, ou pas meilleur que des dates tirées au
  hasard (p_perm > 0,05), ou signe instable d'une année à l'autre.

## Signal
- Type : event (+1 = long, −1 = short)
- Définition exacte (barres 1Dutc, open time UTC, position prise à la clôture de la barre t) :
  - **mon_long** = +1 sur la barre du dimanche (weekday 6) → détention du lundi (h = 1)
  - **tom_long** = +1 sur la barre de l'avant-dernier jour du mois (t + 2 j = le 1er)
    → détention dernier jour + jours 1–3 (h = 4)
  - **wkend_short** = −1 sur la barre du vendredi (weekday 4) → short samedi + dimanche (h = 2)
- Sens : long pour mon_long et tom_long, short pour wkend_short. Le test vs hasard (décalage circulaire des événements, 200 tirages) neutralise
  la dérive haussière ou baissière de la période.

## Données et fenêtres
- Source / TF : perp 1d ; univers : all (40 actifs, BTC et ETH inclus)
- IS : 2021-01-01 → 2024-06-30 ; OOS : 2024-07-01 → fin des données
- Données hors OHLCV : aucune

## Tests
- Horizons (barres) : 1, 2 et 4 pour les trois événements → 9 tests. Horizons « naturels »
  pré-déclarés : mon_long h1, wkend_short h2, tom_long h4 ; les six autres sont des contrôles
  (comptés dans le BH).
- Cible : raw (rendement directionnel brut)
- Coût aller-retour : 0,15 % (une jambe)
- Puissance : ~120 lundis, ~120 week-ends et ~27 changements de mois en OOS (dates, pas événements) ;
  tom_long est sous-dimensionné, un échec de puissance est possible et sera dit.

## Gates (OOS)
Gates par défaut de references/methodology.md §3, mode event, inchangées :
G0 ≥ 50 événements OOS, G1 moyenne et t > 0, G2 p_perm ≤ 0,05, G3 t NW ≥ 2, G4 BH q ≤ 0,10,
G5 IS > 0, G6 ≥ 2/3 des années positives, G7 moyenne − coût > 0 en IS ET en OOS.

## Contexte de tests multiples
~105 tests avant ce run (registre 15 + ~90 antérieurs) ; ce run en ajoute 9.

## Suite prévue selon verdict
- CANDIDAT → backtest pré-enregistré (crypto-backtest-forge) sur BTC/ETH puis panier, funding
  inclus, puis contrôle sur xperp
- PISTE → au plus une v2 pré-déclarée (ex. version intraday 1h), sinon clôture
- REJETÉ → clôture documentée de la famille « saisonnalité daily »
