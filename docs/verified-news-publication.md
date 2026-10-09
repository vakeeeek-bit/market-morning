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
履歴date指定時には当日のdata/history/YYYY-MM-DD/news.jsonだけを表示し、存在しない場合は未保存と明記する。
独立したニュース日付セレクターとdata/news-history.jsonでニュース履歴を選べる。
後日収集はedition=retrospective、実際のupdated_at/collected_at、original_as_of_status=not_reconstructedを必須とする。当日の朝に調査・公開したと偽装しない。
日次朝版の補完では、当日夜の発表を混入させない。発表時刻不明の記事は当日朝時点の既知性を保証しないと記す。
各履歴は部分収集であり、総合レポートの未作成・市場反応・個別株/格付けの網羅を埋めたことにはしない。市場・旧総合レポートと履歴インデックスは変更しない。
