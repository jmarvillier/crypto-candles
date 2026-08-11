# SPEC — contrat de donnees

Ce fichier fige les conventions du repo. **Toute modification invalide les
backtests anterieurs** : versionner le changement et le mentionner dans les
pre-registrations concernees.

## Deux series separees, jamais fusionnees

```
data/<ACTIF>/perp/    perp classique <BASE>-USDT-SWAP, historique profond (2020+)
data/<ACTIF>/xperp/   XPERP EEA <BASE>-USD_UM_XPERP-…, depuis fin mars 2026
```

XPERP et perp classique **ne cotent pas au meme prix**. Les concatener
fabriquerait une serie traversant un saut artificiel : faux breakouts, stops
fixes decales, grilles fausses. Separees, chaque serie est homogene et
directement backtestable.

`compare_sources.py` chiffre l'ecart sur le recouvrement (basis median et son
ecart-type, correlation des rendements, ratio de volume). C'est la mesure qui
dit si un edge valide sur `perp` a des chances de tenir sur `xperp`.

## Format des fichiers

NDJSON : une bougie par ligne, tableau JSON compact. Choisi contre un tableau
JSON unique parce qu'il rend les ajouts *append-only* — un `git diff` montre
`+N lignes` au lieu d'un blob entierement reecrit.

```
[ts, open, high, low, close, vol_base, vol_quote, src]
```

| champ | type | sens |
|---|---|---|
| `ts` | int (epoch ms) | **open time**, UTC strict |
| `open/high/low/close` | float | prix |
| `vol_base` | float | volume en actif de base (OKX `volCcy`) |
| `vol_quote` | float | volume en quote (OKX `volCcyQuote`) |
| `src` | str | `x` XPERP, `s` perp classique, `d` derive par agregation |

`src` est redondant avec le chemin, et c'est voulu : un fichier ou un CSV
exporte reste identifiable hors de son arborescence.

Le volume en **contrats** n'est pas stocke : il depend du `ctVal` de
l'instrument et n'est donc pas comparable d'une serie a l'autre.

## Regles invariantes

1. **Bougies closes uniquement.** OKX renvoie `confirm` en colonne 8 ; les `0`
   sont jetes. Sans ca, la derniere bougie de chaque fetch serait partielle et
   se figerait definitivement dans le fichier.
2. **UTC strict.** Les TF >= 12h utilisent les variantes `…utc` de l'API OKX,
   qui s'aligne sinon sur UTC+8. Les TF <= 4h sont naturellement alignes.
3. **Aucun forward-fill.** Les trous restent des trous et sont documentes dans
   `_meta.json`. Un trou est une information ; une bougie inventee est un
   mensonge qui survit a tous les backtests.
4. **Append-only.** Une bougie deja ecrite n'est jamais modifiee. Un fetch qui
   corrige du passe fait l'objet d'un commit explicite.
5. **Une arborescence, une source.** Aucune bougie `x` dans `perp/` ni
   l'inverse. `validate.py` le verifie.

## Timeframes

| repertoire | `bar` OKX | shard |
|---|---|---|
| `1min` | `1m` | un fichier par mois |
| `5min` `15min` `30min` `1h` `4h` | `5m` `15m` `30m` `1H` `4H` | un fichier par an |
| `12h` `1d` `1w` `1mon` | `12Hutc` `1Dutc` `1Wutc` `1Mutc` | fichier unique |
| `1y` | *(aucun)* | fichier unique, **derive** de `1mon` |

`1Y` n'existe pas dans l'API OKX (plus haut TF natif : `3Mutc`). Le yearly est
agrege localement et porte `src = "d"`.

Nommage : jamais `1m` et `1M` cote a cote — macOS et Windows sont insensibles
a la casse et git y verrait des collisions fantomes. D'ou `1min` / `1mon`.

## Bougies a volume nul

Un instrument fraichement liste renvoie des bougies plates (O=H=L=C, vol=0)
tant qu'aucune transaction n'a eu lieu. La tete morte d'une serie est rognee au
fetch ; celles qui restent au milieu sont reelles (illiquidite) et signalees
par `validate.py` et `--format stats`. Un backtest qui remplit des ordres sur
ces bougies mesure un marche qui n'existait pas.

## Reproductibilite

Taguer chaque snapshot utilise pour une pre-registration
(`git tag data-2026-08-11`) et epingler le SHA dans le document de strategie.
L'OOS scelle devient verifiable : impossible de pretendre apres coup que les
donnees n'avaient pas bouge.
