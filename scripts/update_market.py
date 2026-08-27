import json
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf


SYMBOLS = {
    "sp500": {
        "name": "S&P500",
        "ticker": "^GSPC",
    },
    "nasdaq": {
        "name": "NASDAQ総合",
        "ticker": "^IXIC",
    },
    "nasdaq100": {
        "name": "NASDAQ100",
        "ticker": "^NDX",
    },
    "dow": {
        "name": "NYダウ",
        "ticker": "^DJI",
    },
    "russell2000": {
        "name": "Russell2000",
        "ticker": "^RUT",
    },
    "nikkei225": {
        "name": "日経225",
        "ticker": "^N225",
    },
    "topix": {
    "name": "TOPIX参考（1306 ETF）",
    "ticker": "1306.T",
    },
    "us10y": {
    "name": "米10年債",
    "ticker": "^TNX",
    "dxy": {
        "name": "DXY",
        "ticker": "DX-Y.NYB",
    },
    "usdjpy": {
        "name": "USD/JPY",
        "ticker": "JPY=X",
    },
    "eurusd": {
        "name": "EUR/USD",
        "ticker": "EURUSD=X",
    },
    "gold": {
        "name": "Gold",
        "ticker": "GC=F",
    },
    "silver": {
        "name": "Silver",
        "ticker": "SI=F",
    },
    "copper": {
        "name": "Copper",
        "ticker": "HG=F",
    },
    "wti": {
        "name": "WTI",
        "ticker": "CL=F",
    },
    "brent": {
        "name": "Brent",
        "ticker": "BZ=F",
    },
    "btc": {
        "name": "BTC",
        "ticker": "BTC-USD",
    },
    "eth": {
        "name": "ETH",
        "ticker": "ETH-USD",
    },
}


def get_market_data(symbol, info):
    ticker = yf.Ticker(info["ticker"])

    hist = ticker.history(period="5d", interval="1d")

    if len(hist) < 2:
        return {
            "name": info["name"],
            "ticker": info["ticker"],
            "price": None,
            "change": None,
            "change_pct": None,
            "status": "確認できず",
        }

    latest = hist.iloc[-1]
    previous = hist.iloc[-2]

    price = float(latest["Close"])
    previous_price = float(previous["Close"])

    change = price - previous_price
    change_pct = (change / previous_price) * 100

    return {
        "name": info["name"],
        "ticker": info["ticker"],
        "price": round(price, 4),
        "previous": round(previous_price, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 2),
        "status": "取得成功",
    }


def main():

    now = datetime.now(ZoneInfo("Asia/Tokyo"))

    result = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Tokyo",
        "source": "Yahoo Finance via yfinance",
        "markets": {},
    }

    for key, info in SYMBOLS.items():

        try:
            result["markets"][key] = get_market_data(key, info)

        except Exception as e:

            result["markets"][key] = {
                "name": info["name"],
                "ticker": info["ticker"],
                "price": None,
                "change": None,
                "change_pct": None,
                "status": "取得失敗",
                "error": str(e),
            }


    with open(
        "data/market.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    main()
