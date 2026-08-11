# Repo OHLCV — donnees de backtest

Historiques de bougies OKX pour backtests de strategies. Deux series par actif,
**stockees separement** parce qu'elles ne cotent pas au meme prix.

## Structure

```
data/<ACTIF>/perp/<TF>/<ANNEE>/…    perp classique USDT, profond (2020+)
data/<ACTIF>/xperp/<TF>/<ANNEE>/…   XPERP EEA, depuis fin mars 2026
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
python tools/read_ohlcv.py --repo . --asset BTC --source perp --tf 1h \
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
