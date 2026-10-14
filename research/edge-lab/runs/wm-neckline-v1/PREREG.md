# wm-neckline-v1 — pré-enregistrement

Figé le 2026-10-14, AVANT le premier run (aucun résultat vu). Toute modification après
résultats = nouvelle version (wm-neckline-v2) pré-déclarée, et les deux runs comptent dans le
registre.

GO utilisateur : 2026-10-14 (« oui fais ça »), lancement direct demandé — protocole fixé par
l'assistant sur les choix standards ci-dessous, sans retour intermédiaire.

## Hypothèse
- Idée en une phrase : après un W (double creux) confirmé par une clôture au-dessus de la
  ligne de cou, le prix monte ; après un M (double sommet) confirmé par une clôture sous la
  ligne de cou, il baisse. Question pratique : une figure W/M « solide » justifie-t-elle de
  lancer une grille directionnelle long/short ?
- Mécanisme supposé : un second test raté d'un niveau signale l'épuisement des vendeurs
  (W) ou des acheteurs (M) ; la cassure du cou déclenche les stops du camp piégé et les
  entrées des traders chartistes. Qui paie : le camp piégé au second test. Mécanisme faible —
  figure très connue, donc possiblement arbitrée ; les familles voisines (SMC/ICT,
  sweep→MSS→breaker) ont toutes fini NO-GO.
- Ce qui la falsifierait : rendement moyen OOS ≤ 0, ou pas meilleur que des dates tirées au
  hasard (p_perm > 0,05), ou signe instable d'une année à l'autre.

## Signal
- Type : event (+1 = long après W, −1 = short après M)
- Définition exacte (barres 1Dutc, position prise à la clôture de la barre de cassure) :
  - pivots fractals K = 5 : plus bas (plus haut) strict des barres [i−5, i+5], connu
    seulement à la clôture de i+5 ;
  - deux pivots consécutifs espacés de 10 à 60 barres, d'écart ≤ 3 % ;
  - ligne de cou = plus haut (W) / plus bas (M) entre les deux pivots ;
  - hauteur ≥ 5 % du cou ;
  - événement à la 1re clôture au-delà du cou, au plus 30 barres après la confirmation du
    2e pivot, si aucune clôture n'a franchi le pire des deux pivots entre-temps ;
  - un événement par figure ; cooldown moteur par défaut (h barres).
- Pas de filtre de tendance préalable (W « après une baisse ») : version de base, la plus
  simple. Un filtre de contexte serait une v2.

## Données et fenêtres
- Source / TF : perp 1d ; univers : all (40 actifs, BTC et ETH inclus)
- IS : 2021-01-01 → 2024-06-30 ; OOS : 2024-07-01 → fin des données (2026-10-13)
- Données hors OHLCV : aucune ; DATA_SHA = commit de crypto-candles au lancement

## Tests
- Horizons (barres) : 5, 10, 20 (≈ durée de vie d'une grille directionnelle) × 2 événements
  = 6 tests
- Cible : raw (rendement directionnel brut) ; le test vs hasard (200 décalages circulaires)
  neutralise la dérive du marché (bear 2025-26 qui favoriserait tout short)
- Coût aller-retour : 0,15 % (une jambe)

## Gates (OOS)
Gates par défaut de references/methodology.md §3, mode event, inchangées :
G0 ≥ 50 événements OOS, G1 moyenne et t > 0, G2 p_perm ≤ 0,05, G3 t NW ≥ 2, G4 BH q ≤ 0,10,
G5 IS > 0, G6 ≥ 2/3 des années positives, G7 moyenne − coût > 0 en IS ET en OOS.

## Contexte de tests multiples
~114 tests avant ce run (registre 24 + ~90 antérieurs) ; ce run en ajoute 6.

## Suite prévue selon verdict
- CANDIDAT → backtest pré-enregistré (crypto-backtest-forge) d'une grille directionnelle
  déclenchée par la figure (bornes = pivots / objectif, stop sous les pivots), puis contrôle xperp
- PISTE → au plus une v2 pré-déclarée (filtre de tendance préalable ou K différent), sinon clôture
- REJETÉ → clôture documentée de la famille « figures doubles creux / sommets daily » ; une
  grille directionnelle ne peut pas s'appuyer sur ces figures comme sur un signal
