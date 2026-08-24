import json
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

from django.core.cache import cache


COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=7d"
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
CRYPTO_NEWS_RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"
BINANCE_TICKERS_URL = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_ASSETS = {"BTC": ("bitcoin", "Bitcoin"), "ETH": ("ethereum", "Ethereum"), "BNB": ("binancecoin", "BNB"), "SOL": ("solana", "Solana"), "XRP": ("ripple", "XRP"), "DOGE": ("dogecoin", "Dogecoin"), "TRX": ("tron", "TRON"), "ADA": ("cardano", "Cardano")}


def get_market_assets():
    """Fetch and cache public market data; return None instead of fake values on failure."""
    cache_key = "markets:coingecko:top20"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        request = Request(COINGECKO_MARKETS_URL, headers={"Accept": "application/json", "User-Agent": "CLOUDD 1-Markets/1.0"})
        with urlopen(request, timeout=8) as response:
            assets = json.loads(response.read().decode("utf-8"))
    except Exception:
        assets = _get_binance_assets()
    if assets:
        cache.set(cache_key, assets, 60)
    return assets


def _get_binance_assets():
    """Public fallback with live ticker values if CoinGecko is unavailable."""
    try:
        request = Request(BINANCE_TICKERS_URL, headers={"Accept": "application/json", "User-Agent": "CLOUDD 1-Markets/1.0"})
        with urlopen(request, timeout=8) as response:
            tickers = {ticker["symbol"]: ticker for ticker in json.loads(response.read().decode("utf-8"))}
        assets = []
        for rank, (symbol, (coin_id, name)) in enumerate(BINANCE_ASSETS.items(), start=1):
            ticker = tickers.get(f"{symbol}USDT")
            if ticker:
                assets.append({"id": coin_id, "symbol": symbol.lower(), "name": name, "image": "", "current_price": ticker["lastPrice"], "price_change_percentage_24h": ticker["priceChangePercent"], "market_cap": None, "market_cap_rank": rank, "total_volume": ticker["quoteVolume"], "high_24h": ticker["highPrice"], "low_24h": ticker["lowPrice"]})
        return assets or None
    except Exception:
        return None


def _fetch_json(url, cache_key, seconds=60):
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "CLOUDD 1-Markets/1.0"})
        with urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    cache.set(cache_key, data, seconds)
    return data


def get_market_overview():
    return _fetch_json(COINGECKO_GLOBAL_URL, "markets:global", 60)


def get_market_news():
    cached = cache.get("markets:news")
    if cached is not None:
        return cached
    try:
        request = Request(CRYPTO_NEWS_RSS_URL, headers={"User-Agent": "CLOUDD 1-Markets/1.0"})
        with urlopen(request, timeout=8) as response:
            root = ET.fromstring(response.read())
        articles = []
        for item in root.findall("./channel/item")[:6]:
            articles.append({"title": item.findtext("title"), "url": item.findtext("link"), "published": item.findtext("pubDate"), "source": "CoinDesk"})
    except Exception:
        return None
    cache.set("markets:news", articles, 300)
    return articles
