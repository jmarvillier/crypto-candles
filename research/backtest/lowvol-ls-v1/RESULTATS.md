# lowvol-ls-v1 — résultats (2026-10-13)

**Verdict : NO-GO, 0/7 gates.** Run unique, protocole PREREG inchangé (seul correctif technique
après le GO : arguments `sheet_name=` de l'export Excel, plantage avant tout calcul affiché).

| scénario | rend. annuel | Sharpe | t NW4 | maxDD |
|---|---|---|---|---|
| BASE 2021-2026 | −19,0 % | −0,21 | −0,54 | −82,7 % |
| IS 2021-01 → 2024-06 | −36,5 % | −0,54 | −1,08 | −82,7 % |
| OOS 2024-07 → 2026-10 | +17,3 % | +0,72 | +1,21 | −16,6 % |
| STRESS funding (shorts −11 %/an) | −23,3 % | −0,33 | −0,85 | −84,5 % |
| brut sans coûts | −17,0 % | −0,16 | −0,40 | −82,1 % |
| diag dollar-neutre | −26,3 % | −0,41 | −0,99 | −87,7 % |

Par année (net) : 2021 −81,5 % · 2022 +31,9 % · 2023 +2,9 % · 2024 −8,3 % · 2025 +46,7 % · 2026 −11,9 %.
La jambe short (alts les plus volatiles) perd −202 % (somme des rendements hebdo) en 2021. Le signal est
déjà négatif AVANT coûts : ni le funding ni l'exécution ne sont en cause.

## Pourquoi le lab disait GO (diagnostic post-hoc, diag/)
Même portefeuille quintile, sans couverture ni coûts, moyenne hebdo du spread low-vol − high-vol :
**+61 bps en rendement LOG, −61 bps en rendement SIMPLE** (signe inversé 4 années sur 6).
1. L'IC de rang du lab est réel : l'alt volatile « typique » sous-performe (médiane).
2. Mais la moyenne arithmétique, celle qu'encaisse une position, est portée par quelques
   explosions de queue droite (2021, 2023-24) : shorter les alts volatiles = vendre la loterie.
3. Le log écrase précisément ces queues (−σ²/2) : un spread ou un net de coûts mesuré en log
   surestime mécaniquement tout short de haute vol. C'est le piège « rang ≠ moyenne », aggravé par la cible log.

## Conséquences
- Piste low-vol des alts **close** (NO-GO documenté). Pas de v2 : la pathologie n'est pas mécanique.
- Défaut méthodologique du lab : spread Q5−Q1 et gate « net de coûts » doivent se calculer en
  rendement SIMPLE. Les CANDIDAT de risk-anomalies-v1 (bêta, idio-vol, MAX) relèvent du même biais
  et sont à considérer comme non confirmés.
