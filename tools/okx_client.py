"""Client OKX market data (endpoints PUBLICS uniquement — aucune cle API requise).

Points verifies sur l'API le 2026-08-11 :
  - `history-candles` accepte limit=300 (la doc annonce 100) et pagine vers le
    passe via `after` (= "strictement plus ancien que ce ts").
  - Un User-Agent est OBLIGATOIRE, sinon 403.
  - Les bougies XPERP sont servies par www.okx.com ET my.okx.com (contrairement
    aux endpoints Rubik qui exigent www).
  - `bar` valides : 1m 3m 5m 15m 30m 1H 2H 4H puis 6Hutc 12Hutc 1Dutc 1Wutc
    1Mutc 3Mutc. `1Y` N'EXISTE PAS.
  - 4H est deja aligne UTC (pas de variante 4Hutc).
  - Colonne 8 `confirm` : "1" = bougie close, "0" = en cours. On jette les "0".
"""
import json
import time
import urllib.error
import urllib.request

HEADERS = {"User-Agent": "crypto-candles/1.0", "Accept": "application/json"}
# Les bougies XPERP sont servies par les deux hotes, et `www` mesure ~25 % plus
# rapide (0,39 s contre 0,52 s par requete). `my` reste la reference EEA pour
# tout ce qui touche au compte ; pour la market data publique, on prend le plus
# rapide. Les deux hotes listent aussi les 112 XPERP en FUTURES.
HOST_XPERP = "www.okx.com"
HOST_SWAP = "www.okx.com"

# history-candles : 20 req / 2 s / IP, soit 0,1 s minimum entre deux appels.
# En pratique la latence reseau (0,4 a 1,5 s selon l'heure) domine largement ce
# throttle : il ne se declenche quasiment jamais. Ne pas se fier a MIN_INTERVAL
# pour estimer une duree de fetch — mesurer une requete reelle et multiplier
# par le nombre de pages (bougies / 300).
MIN_INTERVAL = 0.12
_last_call = [0.0]


def _throttle():
    wait = MIN_INTERVAL - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()


def api(host, path, params=None, retries=9):
    qs = ""
    if params:
        qs = "?" + "&".join("%s=%s" % (k, v) for k, v in params.items() if v is not None)
    url = "https://%s%s%s" % (host, path, qs)
    delay = 1.0
    for attempt in range(retries):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            # OKX renvoie des 503 intermittents (mesure : ~1 requete sur 3 lors
            # d'un episode). Avec 5 tentatives, un fetch de 1 700 pages echoue
            # presque a coup sur ; il en faut assez pour que la probabilite
            # cumulee reste negligeable sur toute la pagination.
            if attempt == retries - 1:
                raise RuntimeError("echec reseau sur %s: %s" % (url, e))
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
            continue
        code = payload.get("code")
        if code == "0":
            return payload.get("data", [])
        # 50011 = rate limit : on backoff au lieu d'abandonner
        if code == "50011":
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
            continue
        raise RuntimeError("OKX %s sur %s : %s" % (code, url, payload.get("msg")))
    raise RuntimeError("rate limit persistant sur %s" % url)


def list_instruments(inst_type, host):
    return api(host, "/api/v5/public/instruments", {"instType": inst_type})


def resolve_instruments(asset):
    """asset ('BTC') -> {'xperp': instId|None, 'swap': instId|None, 'listed': ...}.

    Le XPERP est la source de reference (c'est ce qui est reellement trade sur
    le compte EEA) ; le swap USDT sert au backfill profond.
    """
    asset = asset.upper()
    out = {"asset": asset, "xperp": None, "swap": None,
           "xperp_list_ms": None, "ct_val": None}
    for i in list_instruments("FUTURES", HOST_XPERP):
        if "XPERP" in i["instId"] and i.get("uly", "").split("-")[0] == asset:
            if i.get("state") == "live" or out["xperp"] is None:
                out["xperp"] = i["instId"]
                out["xperp_list_ms"] = int(i["listTime"]) if i.get("listTime") else None
                out["ct_val"] = i.get("ctVal")
    cand = "%s-USDT-SWAP" % asset
    for i in list_instruments("SWAP", HOST_SWAP):
        if i["instId"] == cand:
            out["swap"] = cand
            break
    return out


def host_for(inst_id):
    return HOST_XPERP if "XPERP" in inst_id else HOST_SWAP


def fetch_candles(inst_id, bar, since_ms=None, until_ms=None, src=None,
                  max_pages=100000, progress=None):
    """Bougies CLOSES sur [since, until[, chronologiques, au format repo.

    Pagine vers le passe depuis `until` jusqu'a epuisement ou `since`. Renvoie
    [ts, o, h, l, c, vol_base, vol_quote, src].
    """
    host = host_for(inst_id)
    src = src or ("x" if "XPERP" in inst_id else "s")
    cursor = until_ms
    seen = set()
    rows = []
    pages = 0
    while pages < max_pages:
        params = {"instId": inst_id, "bar": bar, "limit": 300}
        if cursor:
            params["after"] = int(cursor)
        data = api(host, "/api/v5/market/history-candles", params)
        pages += 1
        if not data:
            break
        oldest = None
        stop = False
        for c in data:
            ts = int(c[0])
            oldest = ts if oldest is None else min(oldest, ts)
            if c[8] != "1":          # bougie non close
                continue
            if since_ms is not None and ts < since_ms:
                stop = True
                continue
            if ts in seen:
                continue
            seen.add(ts)
            rows.append([ts, float(c[1]), float(c[2]), float(c[3]), float(c[4]),
                         float(c[6]), float(c[7]), src])
        if progress and pages % 20 == 0:
            progress(len(rows), oldest)
        if stop or oldest is None:
            break
        cursor = oldest
    rows.sort(key=lambda r: r[0])

    # Un instrument fraichement liste renvoie des bougies plates a volume nul
    # tant qu'aucune transaction n'a eu lieu. Elles ne sont pas du marche : on
    # rogne cette tete morte, sinon la couture avec le perp classique affiche
    # un faux gap (constate a 2 % sur SUI a l'ouverture des XPERP).
    first_traded = next((i for i, r in enumerate(rows) if r[5] > 0), None)
    if first_traded is None:
        return []
    return rows[first_traded:]
