"""Reject undefined futures and missing essential observations at publication."""
from datetime import datetime
import math
import re

ESSENTIAL = ('sp500', 'nasdaq', 'nasdaq100', 'dow', 'russell2000', 'sox',
             'us2y', 'us10y', 'dxy', 'usdjpy', 'vix', 'gold', 'copper', 'wti', 'brent')
SECTORS = ('xlc', 'xly', 'xlp', 'xle', 'xlf', 'xlv', 'xli', 'xlb', 'xlre', 'xlk', 'xlu')

def validate_observations(market):
    errors = []
    rows = market.get('markets', {})
    for key in ESSENTIAL:
        row = rows.get(key, {})
        price = row.get('price')
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
            errors.append(f'{key}: 必須観測値がありません')
        if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}', str(row.get('market_date', ''))):
            errors.append(f'{key}: 必須観測の基準日不明')
    missing = [key for key in SECTORS if not isinstance(rows.get('sector_' + key, {}).get('price'), (int, float))
               or not rows.get('sector_' + key, {}).get('market_date')]
    if len(missing) >= 3:
        errors.append('米11セクターETFが3系列以上欠測: ' + ', '.join(missing))
    for key in ('gold', 'copper', 'wti', 'brent'):
        row = rows.get(key, {})
        instrument = row.get('instrument', {})
        required = ('exchange', 'contract_month', 'value_kind', 'basis_time', 'source_url')
        if instrument.get('verification_status') != 'verified' or any(not instrument.get(k) for k in required):
            errors.append(f'{key}: 先物の取引所・限月・値種別・基準時刻・証跡の確認不足')
            continue
        if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', str(instrument['contract_month'])):
            errors.append(f'{key}: 限月の形式が不正')
        if instrument['value_kind'] not in ('daily_close', 'settlement', 'current'):
            errors.append(f'{key}: 値種別不明')
        try:
            basis = datetime.fromisoformat(instrument['basis_time'].replace('Z', '+00:00'))
            if basis.utcoffset() is None:
                raise ValueError('timezone missing')
        except (ValueError, TypeError):
            errors.append(f'{key}: 基準時刻とタイムゾーンが必要')
        if not str(instrument['source_url']).startswith('https://') or instrument.get('market_date') != row.get('market_date'):
            errors.append(f'{key}: 出典または観測日の対応が未確認')
    return errors
