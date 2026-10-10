"""Materialize primary-source facts manually verified on 2026-10-10."""
import json
from pathlib import Path

NOW = '2026-10-10T11:46:24+09:00'
ROWS = [
 ('cme-copper-stock-20261009', 'CME/COMEX：銅在庫の日次公式報告を確認', '2026-10-09', 'CME/COMEX', 'https://www.cmegroup.com/delivery_reports/Copper_Stocks.xls', '10月9日公表、活動日10月8日の銅在庫は合計786,330ショートトン。登録在庫475,868、適格在庫310,462。前回合計784,415に対する増加には純入庫1,592と調整323が含まれる。', 'この日次報告では在庫減少を伴う需給逼迫とは判断しない。', '単位はショートトン。LME・SHFEの在庫と単純合算しない。他取引所の対象日在庫は未取得。'),
 ('fed-scf-20261009', 'FRB：2025年家計調査を公表', '2026-10-09', 'FRB', 'https://www.federalreserve.gov/newsevents/pressreleases/other20261009a.htm', '2025年家計調査では2022年比の実質所得中央値が7%増、実質純資産中央値が2%増。所得に対する債務返済が40%を超える世帯割合は6.5%から8.6%へ上昇した。', '米消費の背景資料。所得改善と返済負担増を併せて確認する。', '2025年の調査であり、10月の景気指標や新たな金融政策決定ではない。'),
 ('boj-money-market-20261009', '日銀：短期金融市場調査、機能度の評価が改善', '2026-10-09', '日本銀行', 'https://www.boj.or.jp/paym/market/market2610.htm', '8月に実施した調査は7月末を基準に381先から回答。資金調達残高は前年から減少、運用残高は増加。市場機能度を高いとする回答が低いとする回答を上回り、その差も改善した。', '銀行の資金繰りと短期市場機能を確認する背景資料。', '7月末の調査であり、10月9日の市場残高や新たな政策変更ではない。'),
 ('ofac-icc-20261009', 'OFAC：ICC関連指定と一般許可を公表', '2026-10-09', '米財務省OFAC', 'https://ofac.treasury.gov/recent-actions/20261009', 'OFACはICC関連の団体をSDNに追加し、一定の取引、通信・企業用ソフトウェア、年金、拘束者に関する一般許可13〜16を公表した。', '制裁対象と許可対象を区別して関連取引の条件を確認する。', '市場反応は未確認。個別許可の適用条件を一律に全取引へ拡張しない。'),
 ('ofac-pegasus-20261009', 'OFAC：物流会社との制裁違反和解を公表', '2026-10-09', '米財務省OFAC', 'https://ofac.treasury.gov/recent-actions/20261009', 'Pegasus Worldwide Logisticsは制裁および報告手続きの計10件の見かけ上の違反について175,015ドルで和解した。対象輸入は2023年9月〜2024年2月に行われた。', '物流・商社には制裁対象企業の確認と当局への報告手続きが重要。', '過去の違反に対する措置であり、新たな包括関税ではない。市場反応は未確認。'),
 ('waller-sep-20261008', 'ウォラー理事：SEPの情報価値とインフレへの対応を説明', '2026-10-08', 'FRB', 'https://www.federalreserve.gov/newsevents/speech/waller20261008a.htm', 'ウォラー理事は10月8日の講演で、労働市場は安定する一方インフレは高く、近い将来はインフレに重点を置くとの見解を示した。政策の速度は今後のデータに応じて調整すると説明した。', '金利に敏感なグロース株の判断では追加データと政策見通しを確認する。', '理事個人の見解でありFOMC決定ではない。講演中の75bpの例は政策コミットメントではない。'),
]

def build():
    articles = []
    for ident, title, day, publisher, url, fact, analysis, limitations in ROWS:
        evidence = {'source_read': '公式本文を取得して確認。', 'facts_verified': fact, 'chronology': f'公表日{day}。確認日は2026-10-10。対象期間と公表日を区別。', 'fact_analysis_separation': '公表事実と解釈を別欄に記載し、市場反応を断定しない。', 'limitations': limitations}
        articles.append(dict(id=ident, title=title, published_date=day, publisher=publisher, source_url=url, verification_url=url, fact=fact, analysis=analysis, limitations=limitations, verified_at=NOW, source_type='primary', verification_status='PASS', market_reaction_status='unverified', market_reaction='未確認', verification={key: {'status': 'PASS', 'evidence': value} for key, value in evidence.items()}))
    return dict(report_date='2026-10-10', target_market_date='2026-10-09', updated_at=NOW, publication_mode='verified_news', coverage_status='partial', coverage_note='一次資料の確認済み6件を掲載。全ニュースの網羅・市場反応・総合レポートPASSを意味しません。', articles=articles)

if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'data/news.json'
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n')
