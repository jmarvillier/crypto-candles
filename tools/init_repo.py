#!/usr/bin/env python3
"""Initialise un repo OHLCV vide : structure, documentation, outils versionnes.

Idempotent : ne rature jamais un fichier existant sauf --force. Les outils sont
COPIES dans le repo (repertoire tools/) pour que la donnee et le code qui l'a
produite soient versionnes ensemble — un backtest reste reproductible meme si
le skill evolue.

    python init_repo.py --repo /chemin/vers/repo
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = ["ohlcv_repo.py", "okx_client.py", "sync_pair.py",
         "read_ohlcv.py", "validate.py", "compare_sources.py",
         "reshard.py"]

GITIGNORE = """\
# jamais versionne : identifiants
secrets.json
*.token

__pycache__/
*.pyc
*.tmp
.cache/
.venv/
# caches Parquet locaux, non versionnes (voir SPEC.md)
cache/
*.parquet
"""

GITATTRIBUTES = """\
*.ndjson text eol=lf
*.json   text eol=lf
*.py     text eol=lf
"""

SPEC = """\
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
| `1min` | `1m` | `<TF>/<ANNEE>/<AAAA-MM>.ndjson` |
| `5min` `15min` `30min` `1h` `4h` `12h` `1d` | `5m` `15m` `30m` `1H` `4H` `12Hutc` `1Dutc` | `<TF>/<ANNEE>/<AAAA>.ndjson` |
| `1w` `1mon` | `1Wutc` `1Mutc` | `<TF>/<TF>.ndjson` |
| `1y` | *(aucun)* | `<TF>/<TF>.ndjson`, **derive** de `1mon` |

Tout ce qui est **sous l'hebdomadaire** a un sous-repertoire annuel : la
structure reste uniforme quand on parcourt le repo a la main. Le 1min descend
au mois (2,7 Mo par mois ; un fichier annuel serait lourd a differ).

A partir du `1w`, fichier unique — et c'est deliberé : une bougie hebdomadaire
peut chevaucher deux annees (semaine du 30/12) et une bougie annuelle
n'appartient a aucun repertoire d'annee. Les sharder imposerait une convention
arbitraire qu'il faudrait connaitre pour lire correctement. Volumes concernes :
29 Ko de weekly et 7 Ko de monthly sur six ans.

`reshard.py` remet un repo existant en conformite si cette regle change.

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
"""

README = """\
# Repo OHLCV — donnees de backtest

Historiques de bougies OKX pour backtests de strategies. Deux series par actif,
**stockees separement** parce qu'elles ne cotent pas au meme prix.

## Structure

```
data/<ACTIF>/perp/<TF>/<ANNEE>/…    perp classique USDT, profond (2020+)
data/<ACTIF>/xperp/<TF>/<ANNEE>/…   XPERP EEA, depuis fin mars 2026
                                    (1w, 1mon, 1y : fichier unique sans annee)
data/<ACTIF>/<source>/_meta.json    couverture, trous par TF
meta/instruments.json               mapping actif -> instId
tools/                              fetch, lecture, validation, comparaison
SPEC.md                             contrat de donnees (a lire avant tout usage)
```

## Usage

```bash
# inventaire
python tools/read_ohlcv.py --repo . --list

# lire des bougies (--source est obligatoire quand les deux existent)
python tools/read_ohlcv.py --repo . --asset BTC --source perp --tf 1h \\
    --from 2022-01-01 --to 2025-01-01 --format csv -o btc1h.csv

# couverture avant un backtest
python tools/read_ohlcv.py --repo . --asset BTC --source perp --tf 5min --format stats

# a quel point un edge valide sur perp peut tenir sur xperp
python tools/compare_sources.py --repo . --asset BTC --tf 1h

# ajouter un actif / mettre a jour
python tools/sync_pair.py --repo . --asset SOL --mode init
python tools/sync_pair.py --repo . --asset all --mode update

# controle avant commit
python tools/validate.py --repo .

# remettre le decoupage des fichiers en conformite apres un changement de SPEC
python tools/reshard.py --repo . --dry-run
```

Depuis Python :

```python
import sys; sys.path.insert(0, "tools")
from read_ohlcv import load
rows = load(".", "BTC", "perp", "1h", "2022-01-01", "2025-01-01")
```

## A savoir

- Seules les **bougies closes** sont stockees, timestamps en **open time UTC**.
- `perp` sert a construire et valider ; `xperp` sert a verifier qu'un edge
  survit sur l'instrument reellement trade. Les deux fenetres n'ont ni la meme
  profondeur ni le meme regime de marche.
- Les trous ne sont pas comblees par interpolation ; ils sont listes dans
  `_meta.json`.
"""


def write(path, content, force=False):
    if os.path.exists(path) and not force:
        print("  = %s (existe deja)" % os.path.relpath(path))
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)
    print("  + %s" % os.path.relpath(path))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--force", action="store_true",
                    help="ecrase README/SPEC/outils existants")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    os.makedirs(repo, exist_ok=True)
    print("Initialisation de %s" % repo)

    for d in ("data", "meta", "tools"):
        os.makedirs(os.path.join(repo, d), exist_ok=True)

    write(os.path.join(repo, "README.md"), README, args.force)
    write(os.path.join(repo, "SPEC.md"), SPEC, args.force)
    write(os.path.join(repo, ".gitignore"), GITIGNORE, args.force)
    write(os.path.join(repo, ".gitattributes"), GITATTRIBUTES, args.force)
    write(os.path.join(repo, "meta", "instruments.json"), "{}\n", False)

    print("Outils :")
    for t in TOOLS:
        dst = os.path.join(repo, "tools", t)
        if os.path.exists(dst) and not args.force:
            print("  = tools/%s (existe deja)" % t)
            continue
        shutil.copy2(os.path.join(HERE, t), dst)
        print("  + tools/%s" % t)

    print("\nRepo pret. Etape suivante :\n"
          "  python tools/sync_pair.py --repo %s --pair BTC --mode init" % args.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
