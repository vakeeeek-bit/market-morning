# 確認済みニュースの独立公開

ユーザー承認：2026-10-09。確認済みニュースを市場欠測と切り離す。

data/news.json は世界市場・日本株画面で共通表示する。記事ごとの一次出典、
発表日、確認日時、確認証跡、事実と解釈の分離、未確認の市場反応を明示する。
python scripts/validate_data.py --scope news で検証する。
ニュースを更新するときは、両ページで日付・記事・市場更新状態を確認する。

これは総合レポートのPASSではない。report.json、japan-stocks.json、
research-evidence.json、market.jsonの既存ゲートは変更しない。
市場数値の未確認をニュース記事内の推測値で補完しない。
記事の採用範囲をcoverage_noteに記録し、調査全体のPASSを名乗らない。
履歴date指定時には最新ニュースを表示しない。
