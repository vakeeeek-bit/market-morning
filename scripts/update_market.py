import json
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf


SYMBOLS = {
    "sp500": {"name": "S&P500", "ticker": "^GSPC"},
    "nasdaq": {"name": "NASDAQ総合", "ticker": "^IXIC"},
    "nasdaq100": {"name": "NASDAQ100", "ticker": "^NDX"},
    "dow": {"name": "NYダウ", "ticker": "^DJI"},
    "russell2000": {"name": "Russell2000", "ticker": "^RUT"},
    "nikkei225": {"name": "日経225", "ticker": "^N225"},
    "topix": {
        "name": "TOPIX参考（1306 ETF）",
        "ticker": "1306.T",
    },
    "dxy": {"name": "DXY", "ticker": "DX-Y.NYB"},
    "usdjpy": {"name": "USD/JPY", "ticker": "JPY=X"},
    "eurusd": {"name": "EUR/USD", "ticker": "EURUSD=X"},
    "us10y": {"name": "米10年債利回り", "ticker": "^TNX"},
    "vix": {"name": "VIX", "ticker": "^VIX"},
    "gold": {"name": "Gold", "ticker": "GC=F"},
    "silver": {"name": "Silver", "ticker": "SI=F"},
    "copper": {"name": "Copper", "ticker": "HG=F"},
    "wti": {"name": "WTI", "ticker": "CL=F"},
    "brent": {"name": "Brent", "ticker": "BZ=F"},
    "btc": {"name": "BTC", "ticker": "BTC-USD"},
    "eth": {"name": "ETH", "ticker": "ETH-USD"},
}


def empty_market(info, status, error=None):
    result = {
        "name": info["name"],
        "ticker": info["ticker"],
        "price": None,
        "previous": None,
        "change": None,
        "change_pct": None,
        "status": status,
        "market_date": None,
        "previous_market_date": None,
    }
    if error:
        result["error"] = error
    return result


def get_market_data(info):
    ticker = yf.Ticker(info["ticker"])
    hist = ticker.history(period="7d", interval="1d")

    if hist.empty or len(hist) < 2:
        return empty_market(info, "確認できず")

    latest = hist.iloc[-1]
    previous = hist.iloc[-2]

    price = float(latest["Close"])
    previous_price = float(previous["Close"])
    change = price - previous_price
    change_pct = (
        (change / previous_price) * 100
        if previous_price != 0
        else None
    )

    latest_index = hist.index[-1]
    previous_index = hist.index[-2]

    return {
        "name": info["name"],
        "ticker": info["ticker"],
        "price": round(price, 4),
        "previous": round(previous_price, 4),
        "change": round(change, 4),
        "change_pct": (
            round(change_pct, 2)
            if change_pct is not None
            else None
        ),
        "status": "取得成功",
        "market_date": latest_index.strftime("%Y-%m-%d"),
        "previous_market_date": previous_index.strftime("%Y-%m-%d"),
    }


def get_fred_2y():
    """
    FREDのDGS2（日次・米2年国債利回り）をCSVで取得。
    yfinanceに安定した2年債利回り指数が見当たらないため、
    2年金利だけ公式FREDを利用する。
    """
    url = (
        "https://fred.stlouisfed.org/graph/"
        "fredgraph.csv?id=DGS2"
    )

    hist = yf.download  # requirements互換確認用ではなく未使用

    import pandas as pd

    df = pd.read_csv(url)
    df["DGS2"] = pd.to_numeric(
        df["DGS2"],
        errors="coerce"
    )
    df = df.dropna(subset=["DGS2"])

    if len(df) < 2:
        return {
            "name": "米2年債利回り",
            "ticker": "FRED:DGS2",
            "price": None,
            "previous": None,
            "change": None,
            "change_pct": None,
            "status": "確認できず",
            "market_date": None,
            "previous_market_date": None,
        }

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(latest["DGS2"])
    previous_price = float(previous["DGS2"])
    change = price - previous_price
    change_pct = (
        (change / previous_price) * 100
        if previous_price != 0
        else None
    )

    return {
        "name": "米2年債利回り",
        "ticker": "FRED:DGS2",
        "price": round(price, 4),
        "previous": round(previous_price, 4),
        "change": round(change, 4),
        "change_pct": (
            round(change_pct, 2)
            if change_pct is not None
            else None
        ),
        "status": "取得成功",
        "market_date": str(latest["DATE"]),
        "previous_market_date": str(previous["DATE"]),
    }


def calculate_2s10s(us2y, us10y):
    if (
        us2y.get("price") is None
        or us10y.get("price") is None
    ):
        return {
            "name": "米2年-10年スプレッド",
            "value_pct_point": None,
            "value_bp": None,
            "previous_pct_point": None,
            "previous_bp": None,
            "change_bp": None,
            "curve": "確認できず",
            "status": "確認できず",
        }

    current = us10y["price"] - us2y["price"]

    previous = None
    change_bp = None

    if (
        us2y.get("previous") is not None
        and us10y.get("previous") is not None
    ):
        previous = (
            us10y["previous"]
            - us2y["previous"]
        )
        change_bp = (current - previous) * 100

    if current > 0:
        curve = "順イールド"
    elif current < 0:
        curve = "逆イールド"
    else:
        curve = "フラット"

    return {
        "name": "米2年-10年スプレッド",
        "value_pct_point": round(current, 4),
        "value_bp": round(current * 100, 1),
        "previous_pct_point": (
            round(previous, 4)
            if previous is not None
            else None
        ),
        "previous_bp": (
            round(previous * 100, 1)
            if previous is not None
            else None
        ),
        "change_bp": (
            round(change_bp, 1)
            if change_bp is not None
            else None
        ),
        "curve": curve,
        "status": "計算成功",
        "formula": "米10年債利回り - 米2年債利回り",
    }


def build_data_quality(markets):
    success = []
    failed = []

    for key, item in markets.items():
        if item.get("status") == "取得成功":
            success.append(key)
        else:
            failed.append(key)

    return {
        "total": len(markets),
        "success_count": len(success),
        "failed_count": len(failed),
        "success_rate_pct": round(
            len(success) / len(markets) * 100,
            1
        ) if markets else 0,
        "failed_keys": failed,
    }


def main():
    now = datetime.now(
        ZoneInfo("Asia/Tokyo")
    )

    result = {
        "updated_at": now.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "timezone": "Asia/Tokyo",
        "source": (
            "Yahoo Finance via yfinance; "
            "FRED DGS2 for US 2Y Treasury yield"
        ),
        "notes": {
            "topix": (
                "TOPIXそのものではなく1306.T"
                "（TOPIX連動ETF）を参考値として使用"
            ),
            "us10y": (
                "^TNXを米10年債利回りとして使用"
            ),
            "us2y": (
                "米2年債利回りはFRED DGS2を使用。"
                "公表タイミングの違いにより、"
                "米10年債と基準日がずれる場合があります"
            ),
            "us_2s10s": (
                "米10年債利回り - 米2年債利回り。"
                "両系列のmarket_dateも確認してください"
            ),
            "vix": "^VIXをVIX指数として使用",
        },
        "markets": {},
        "derived": {},
        "data_quality": {},
    }

    for key, info in SYMBOLS.items():
        try:
            result["markets"][key] = (
                get_market_data(info)
            )
        except Exception as e:
            result["markets"][key] = (
                empty_market(
                    info,
                    "取得失敗",
                    str(e)
                )
            )

    try:
        result["markets"]["us2y"] = get_fred_2y()
    except Exception as e:
        result["markets"]["us2y"] = {
            "name": "米2年債利回り",
            "ticker": "FRED:DGS2",
            "price": None,
            "previous": None,
            "change": None,
            "change_pct": None,
            "status": "取得失敗",
            "market_date": None,
            "previous_market_date": None,
            "error": str(e),
        }

    result["derived"]["us_2s10s"] = (
        calculate_2s10s(
            result["markets"]["us2y"],
            result["markets"]["us10y"],
        )
    )

    result["data_quality"] = (
        build_data_quality(result["markets"])
    )

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
