/* Every component has its own as-of date. Collection success is not report PASS. */
(() => {
  const el = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
  const read = async path => {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) return null;
    return response.json();
  };
  let sequence = 0;
  let lastDate = new URLSearchParams(location.search).get('date');
  const host = el('section', ''); host.id = 'publication-health'; host.className = 'section';
  const anchor = document.getElementById('quick-view') || document.getElementById('verified-news');
  anchor?.before(host);
  async function render() {
    const request = ++sequence;
    const date = new URLSearchParams(location.search).get('date');
    const prefix = /^20\d{2}-\d{2}-\d{2}$/.test(date || '') ? `/data/history/${date}` : '/data';
    const [report, news, market, japan, attempt] = await Promise.all([
      read(`${prefix}/report.json`), read(`${prefix}/news.json`), read(`${prefix}/market.json`),
      read(`${prefix}/japan-market.json`), date ? Promise.resolve(null) : read('/data/collection-status.json')
    ]).catch(() => [null, null, null, null, null]);
    if (request !== sequence) return;
    host.replaceChildren(el('h2', date ? `${date} の保存・確認状況` : '最新の収集・更新状況'));
    const dates = [...new Set(Object.values(market?.markets || {}).map(r => r.market_date).filter(Boolean))].sort();
    const summary = [
      ['総合レポート', report ? `${report.report_date}版・対象市場 ${report.target_market_date}・品質 ${report.data_quality?.overall || '不明'}` : '未作成・未保存'],
      ['確認済みニュース', news ? `${news.report_date}版・${news.articles.length}件・部分収集` : '未保存'],
      ['世界市場データ', market ? `取得 ${market.updated_at}・基準日 ${dates.join(' / ')}（現在値ではありません）` : '未保存'],
      ['日本株実績', japan ? `${japan.market_date}・更新 ${japan.updated_at}` : '未保存']
    ];
    for (const [name, value] of summary) host.append(el('p', `${name}：${value}`));
    host.append(el('p', 'ニュース・市場実績・総合分析は別々に更新されます。総合レポートが古い場合、以下の見通しは最新日の判断ではありません。'));
    if (attempt) {
      host.append(el('p', `今回の収集：${attempt.checked_at}｜市場 ${attempt.market_attempt_status}｜${attempt.market_attempt_note}`));
      host.append(el('p', `日本株の取引日程：${attempt.japan_calendar_note}`));
    }
    if (report) {
      const day = report.report_date;
      const context = document.getElementById('report-date');
      if (context) context.textContent = `総合分析：${day}版（対象 ${report.target_market_date}）｜最新の日本株実績・ニュースは別日付で表示`;
      const headings = {
        'quick-view-title': `総合分析の要点｜${day}版`,
        'quick-conclusion-label': `${day}版の市場の結論`,
        'quick-events-label': `${day}版の確認項目`,
      };
      for (const [id, label] of Object.entries(headings)) {
        const target = document.getElementById(id); if (target) target.textContent = label;
      }
      for (const id of ['story-sections', 'rating-changes', 'scenario-review']) {
        const target = document.getElementById(id);
        if (target && !target.querySelector('.publication-asof')) {
          const note = el('p', `参照する総合分析：${day}版。前営業日・本日版とは限りません。`);
          note.className = 'publication-asof'; target.prepend(note);
        }
      }
    }
    const quality = document.getElementById('data-quality-status');
    if (quality) quality.textContent = '日本株の取得状態（総合レポート・調査品質とは別）';
  }
  const mode = document.getElementById('history-mode');
  if (mode) new MutationObserver(() => {
    const date = new URLSearchParams(location.search).get('date');
    if (date !== lastDate) { lastDate = date; render(); }
  }).observe(mode, {childList: true});
  window.addEventListener('popstate', render);
  render();
})();
