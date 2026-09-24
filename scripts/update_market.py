import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf


SYMBOLS = {
    "sp500": {"name": "S&P500", "ticker": "^GSPC"},
    "nasdaq": {"name": "NASDAQ総合", "ticker": "^IXIC"},
    "nasdaq100": {"name": "NASDAQ100", "ticker": "^NDX"},
    "sox": {"name": "PHLX半導体株指数（SOX）", "ticker": "^SOX"},
    "dow": {"name": "NYダウ", "ticker": "^DJI"},
    "russell2000": {"name": "Russell2000", "ticker": "^RUT"},
    "nikkei225": {"name": "日経225", "ticker": "^N225"},
    "topix": {"name": "TOPIX参考（1306 ETF）", "ticker": "1306.T"},
    "dxy": {"name": "DXY", "ticker": "DX-Y.NYB"},
    "usdjpy": {"name": "USD/JPY", "ticker": "JPY=X"},
    "eurusd": {"name": "EUR/USD", "ticker": "EURUSD=X"},
    "us10y": {"name": "米10年債利回り", "ticker": "^TNX"},
    "vix": {"name": "VIX", "ticker": "^VIX"},
    "sector_xlc": {"name": "米コミュニケーション・サービス（XLC）", "ticker": "XLC"},
    "sector_xly": {"name": "米一般消費財（XLY）", "ticker": "XLY"},
    "sector_xlp": {"name": "米生活必需品（XLP）", "ticker": "XLP"},
    "sector_xle": {"name": "米エネルギー（XLE）", "ticker": "XLE"},
    "sector_xlf": {"name": "米金融（XLF）", "ticker": "XLF"},
    "sector_xlv": {"name": "米ヘルスケア（XLV）", "ticker": "XLV"},
    "sector_xli": {"name": "米資本財（XLI）", "ticker": "XLI"},
    "sector_xlb": {"name": "米素材（XLB）", "ticker": "XLB"},
    "sector_xlre": {"name": "米不動産（XLRE）", "ticker": "XLRE"},
    "sector_xlk": {"name": "米情報技術（XLK）", "ticker": "XLK"},
    "sector_xlu": {"name": "米公益（XLU）", "ticker": "XLU"},
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


def finite_float(value, label):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label}が有効な数値ではありません")
    return number


def get_market_data(info, prior_snapshots=None):
    ticker = yf.Ticker(info["ticker"])
    hist = ticker.history(period="7d", interval="1d")

    if hist.empty or "Close" not in hist.columns:
        return empty_market(info, "確認できず")

    # 取引途中やデータ障害でCloseがNaNの行を除外する。
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 2:
        return empty_market(info, "確認できず")

    latest = hist.iloc[-1]
    previous = hist.iloc[-2]
    price = finite_float(latest["Close"], "最新終値")
    previous_price = finite_float(previous["Close"], "前日終値")
    latest_index = hist.index[-1]
    previous_index = hist.index[-2]
    latest_market_date = latest_index.strftime("%Y-%m-%d")
    previous_market_date = previous_index.strftime("%Y-%m-%d")

    # Yahooの短期履歴が中間営業日を一時的に欠落させる場合がある。
    # 直前に検証・保存した同一tickerの終値が履歴より新しければ、
    # それを前日終値として使い、複数日変化を「前日比」と誤表示しない。
    if isinstance(prior_snapshots, dict):
        prior_snapshots = [prior_snapshots]
    candidates = []
    for prior_snapshot in prior_snapshots or []:
        if not isinstance(prior_snapshot, dict):
            continue
        prior_date = prior_snapshot.get("market_date")
        prior_price = prior_snapshot.get("price")
        if (
            prior_snapshot.get("status") == "取得成功"
            and prior_snapshot.get("ticker") == info["ticker"]
            and isinstance(prior_date, str)
            and previous_market_date < prior_date < latest_market_date
            and isinstance(prior_price, (int, float))
        ):
            candidates.append((prior_date, finite_float(prior_price, "保存済み前日終値")))
    if candidates:
        previous_market_date, previous_price = max(candidates, key=lambda item: item[0])

    change = price - previous_price
    change_pct = (change / previous_price) * 100 if previous_price != 0 else None

    return {
        "name": info["name"],
        "ticker": info["ticker"],
        "price": round(price, 4),
        "previous": round(previous_price, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
        "status": "取得成功",
        "market_date": latest_market_date,
        "previous_market_date": previous_market_date,
    }


def get_fred_2y():
    import pandas as pd

    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"
    df = pd.read_csv(url)

    if "DGS2" not in df.columns or len(df.columns) < 2:
        raise ValueError(f"FRED DGS2 CSVの列を確認できません: {list(df.columns)}")

    date_column = df.columns[0]
    df["DGS2"] = pd.to_numeric(df["DGS2"], errors="coerce")
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
    price = finite_float(latest["DGS2"], "米2年債最新値")
    previous_price = finite_float(previous["DGS2"], "米2年債前日値")
    change = price - previous_price
    change_pct = (change / previous_price) * 100 if previous_price != 0 else None

    return {
        "name": "米2年債利回り",
        "ticker": "FRED:DGS2",
        "price": round(price, 4),
        "previous": round(previous_price, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
        "status": "取得成功",
        "market_date": str(latest[date_column]),
        "previous_market_date": str(previous[date_column]),
    }


def calculate_2s10s(us2y, us10y):
    if us2y.get("price") is None or us10y.get("price") is None:
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

    if (
        not us2y.get("market_date")
        or not us10y.get("market_date")
        or us2y["market_date"] != us10y["market_date"]
    ):
        return {
            "name": "米2年-10年スプレッド",
            "value_pct_point": None,
            "value_bp": None,
            "previous_pct_point": None,
            "previous_bp": None,
            "change_bp": None,
            "curve": "基準日不一致",
            "status": "基準日不一致",
            "us2y_market_date": us2y.get("market_date"),
            "us10y_market_date": us10y.get("market_date"),
            "formula": "米10年債利回り - 米2年債利回り",
        }

    current = us10y["price"] - us2y["price"]
    previous = None
    change_bp = None

    if us2y.get("previous") is not None and us10y.get("previous") is not None:
        previous = us10y["previous"] - us2y["previous"]
        change_bp = (current - previous) * 100

    curve = "順イールド" if current > 0 else "逆イールド" if current < 0 else "フラット"

    return {
        "name": "米2年-10年スプレッド",
        "value_pct_point": round(current, 4),
        "value_bp": round(current * 100, 1),
        "previous_pct_point": round(previous, 4) if previous is not None else None,
        "previous_bp": round(previous * 100, 1) if previous is not None else None,
        "change_bp": round(change_bp, 1) if change_bp is not None else None,
        "curve": curve,
        "status": "計算成功",
        "formula": "米10年債利回り - 米2年債利回り",
    }


def build_data_quality(markets):
    success = [key for key, item in markets.items() if item.get("status") == "取得成功"]
    failed = [key for key, item in markets.items() if item.get("status") != "取得成功"]
    return {
        "total": len(markets),
        "success_count": len(success),
        "failed_count": len(failed),
        "success_rate_pct": round(len(success) / len(markets) * 100, 1) if markets else 0,
        "failed_keys": failed,
    }


def main():
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    previous_market_sets = []
    market_path = Path("data/market.json")
    if market_path.exists():
        try:
            previous_market_sets.append(json.loads(market_path.read_text(encoding="utf-8")).get("markets", {}))
        except (json.JSONDecodeError, OSError):
            pass
    history_root = Path("data/history")
    for archive_path in sorted(history_root.glob("*/market.json"), reverse=True)[:7]:
        try:
            previous_market_sets.append(json.loads(archive_path.read_text(encoding="utf-8")).get("markets", {}))
        except (json.JSONDecodeError, OSError):
            continue
    result = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Tokyo",
        "source": "Yahoo Finance via yfinance for market closes; FRED DGS2 for US 2Y Treasury yield",
        "notes": {
            "basis": "priceは各tickerの取得可能な最新日足Close。market_dateを必ず併記し、取引中値や日中高値として扱わない",
            "topix": "TOPIXそのものではなく1306.T（TOPIX連動ETF）を参考値として使用",
            "sox": "^SOXをPHLX半導体株指数の参考終値として使用",
            "us_sectors": "S&P500の11業種そのものではなく、各Sector SPDR ETFの日足終値をセクター強弱の参考値として使用",
            "us10y": "^TNXを米10年債利回りとして使用",
            "us2y": "米2年債利回りはFRED DGS2を使用。公表タイミングの違いにより、米10年債と基準日がずれる場合があります",
            "us_2s10s": "米10年債利回り - 米2年債利回り。両系列のmarket_dateも確認してください",
            "vix": "^VIXをVIX指数として使用",
        },
        "markets": {},
        "derived": {},
        "data_quality": {},
    }

    for key, info in SYMBOLS.items():
        try:
            result["markets"][key] = get_market_data(
                info,
                [market_set.get(key) for market_set in previous_market_sets],
            )
        except Exception as error:
            result["markets"][key] = empty_market(info, "取得失敗", str(error))

    try:
        result["markets"]["us2y"] = get_fred_2y()
    except Exception as error:
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
            "error": str(error),
        }

    result["derived"]["us_2s10s"] = calculate_2s10s(
        result["markets"]["us2y"],
        result["markets"]["us10y"],
    )
    result["data_quality"] = build_data_quality(result["markets"])

    with open("data/market.json", "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )


if __name__ == "__main__":
    main()
