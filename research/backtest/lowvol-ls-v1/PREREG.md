# lowvol-ls-v1 — pré-enregistrement du backtest
Figé le 2026-10-13, AVANT tout run (commit 46b44b8). GO de Jérémie reçu le 2026-10-13 21:38 avant tout run, protocole inchangé.
Origine : « Suite ouverte » du journal edge-lab (vol_30 GO au factor lab du 12/10, confirmé par risk-anomalies-v1).

## Avertissement de départ
vol_30 a été découverte sur ces mêmes données (perp 1d, 2021-2026). Ce backtest mesure si l'effet
statistique survit à une implémentation réaliste (coûts, couverture, rotation) ; ce n'est PAS une
validation indépendante. Un GO ici reste « in-sample » et ouvre une validation forward (paper).

## Stratégie (une seule version, aucune grille)
- Univers : 39 alts perp USDT (BTC = couverture). Éligible à la date t si ≥ 120 barres 1d depuis
  la première bougie et volume > 0 sur les 30 derniers jours.
- Signal : vol_30 = écart-type des log-rendements 1d sur 30 j (min 20), calculé à la clôture de t.
- Rebalancement hebdomadaire : à la clôture de la barre 1d du dimanche (lundi 00:00 UTC).
- Jambes : n = max(3, round(N/5)) alts. LONG les n plus basses vol_30, SHORT les n plus hautes.
  Équipondéré : +0,5/n par long, −0,5/n par short (exposition brute alts = 1).
- Couverture bêta : β90 = MCO 90 j des log-rendements 1d vs BTC (min 60), borné [0 ; 3].
  Position BTC = −Σ wᵢ·βᵢ (portefeuille neutre en bêta BTC, réplique la cible « res » du lab).
- Poids ramenés à la cible chaque semaine ; rendements de la semaine = rendements simples
  close→close des actifs × poids cibles (dérive intra-semaine ignorée).

## Coûts
- Alts : 0,05 % taker + 5 bps de glissement par côté, sur Σ|Δw|. BTC : 0,05 % + 2 bps.
- Funding : pas d'historique OKX au-delà de ~3 mois. Scénario BASE = 0 net.
  Scénario STRESS = la jambe short paie 11 %/an sur son notionnel (≈ 0,01 %/8 h en permanence).
  Descriptif : funding de break-even (taux annuel payé par la jambe short qui annule le net).

## Périodes
Du 2021-01-04 au 2026-10-12. IS 2021-01 → 2024-06-30 ; OOS 2024-07-01 → fin (mêmes fenêtres que le lab).

## Gates (toutes requises pour GO in-sample, scénario BASE sauf G6)
- G1 Sharpe annualisé net (rendements hebdo, ×√52) ≥ 0,5 sur la période complète.
- G2 t de Newey-West (lag 4) du rendement hebdo net ≥ 2,0.
- G3 rendement net cumulé > 0 en IS ET en OOS.
- G4 ≥ 4 années civiles sur 6 positives (2026 partielle comptée).
- G5 stress saison des alts : 2021 net ≥ −15 % ET maxDD net (hebdo) ≤ 25 %.
- G6 stress funding : rendement net annualisé > 0 dans le scénario STRESS.
- G7 coûts de transaction < 50 % du rendement brut.

## Diagnostics descriptifs (hors gates, ne changent pas le verdict)
Variante dollar-neutre sans couverture BTC ; contribution jambe long vs jambe short ; rotation ;
rendements par année et par trimestre ; funding de break-even ; nombre d'alts par jambe.

## Issues
GO in-sample → paper forward sur xperp via crypto-live-forge (pas de capital avant).
NO-GO → clôture documentée de la piste low-vol (une v2 au plus, pré-déclarée, visant une pathologie chiffrée).
