/* Quality evidence stays available without competing with the morning brief. */
(() => {
  const el = (tag, text, className = '') => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const read = async path => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(path, {cache: 'no-store', signal: controller.signal});
      if (!response.ok) return null;
      return await response.json();
    } catch { return null; }
    finally { clearTimeout(timer); }
  };

  let sequence = 0;
  let lastDate = new URLSearchParams(location.search).get('date');
  const qualitySection = document.getElementById('quality-section');
  const host = el('details', '', 'disclosure publication-health');
  host.id = 'publication-health';
  host.append(el('summary', '更新日・取得状況・品質ゲート'));
  const body = el('div', '', 'disclosure-body publication-health-body');
  host.append(body);
  qualitySection?.append(host);

  async function render() {
    const request = ++sequence;
    const date = new URLSearchParams(location.search).get('date');
    const prefix = /^20\d{2}-\d{2}-\d{2}$/.test(date || '') ? `/data/history/${date}` : '/data';
    const [report, news, market, japan, attempt, audit, unresolved] = await Promise.all([
      read(`${prefix}/report.json`), read(`${prefix}/news.json`), read(`${prefix}/market.json`),
      read(`${prefix}/japan-market.json`), date ? Promise.resolve(null) : read('/data/collection-status.json'),
      date ? Promise.resolve(null) : read('/data/site-audit.json'),
      date ? Promise.resolve(null) : read('/data/unresolved-items.json')
    ]);
    if (request !== sequence) return;
    body.replaceChildren();

    const dates = [...new Set(Object.values(market?.markets || {}).map(row => row.market_date).filter(Boolean))].sort();
    const decision = report?.publication_policy?.status || report?.data_quality?.overall || '確認できず';
    body.append(el('p', date ? `${date} の保存・確認状況` : `公開判定：${decision}`, 'publication-health-lead'));
    const list = el('ul', '', 'publication-health-list');
    [
      ['総合分析', report ? `${report.report_date}版｜対象市場 ${report.target_market_date}｜更新 ${report.updated_at}` : '未作成・未保存'],
      ['確認済みニュース', news ? `${news.report_date}版｜${news.articles.length}件｜確認 ${news.updated_at}` : '未保存'],
      ['世界市場', market ? `基準日 ${dates.join(' / ')}｜取得 ${market.updated_at}｜${market.data_quality?.publication_status || '旧形式'}` : '未保存'],
      ['日本株実績', japan ? `${japan.market_date}｜更新 ${japan.updated_at}｜${japan.data_state?.label || japan.data_phase || '状態不明'}` : '未保存']
    ].forEach(([name, value]) => list.append(el('li', `${name}：${value}`)));
    body.append(list);
    body.append(el('p', 'ニュース・市場実績・総合分析は独立して更新されます。異なる基準日の数値を同一時点として扱わないでください。'));

    if (attempt) {
      const attemptDay = String(attempt.checked_at || '').slice(0, 10);
      body.append(el('p', `収集記録（${attemptDay}）：${attempt.market_attempt_status}｜${attempt.market_attempt_note}`));
      body.append(el('p', `日本株の取引日程：${attempt.japan_calendar_note}`));
    }
    const reportUpdatedAt = Date.parse(report?.updated_at || '');
    const auditCheckedAt = Date.parse(audit?.checked_at || '');
    const auditIsCurrent = audit && (
      !report || !Number.isFinite(reportUpdatedAt) || !Number.isFinite(auditCheckedAt) || auditCheckedAt > reportUpdatedAt
    );
    if (auditIsCurrent) {
      body.append(el('p', `全体点検：${audit.checked_at}｜${audit.report_publication_status}`));
      for (const row of audit.blockers || []) body.append(el('p', `未解決：${row.title || row.item}｜${row.next_action}`));
    }
    if (unresolved?.items?.length) body.append(el('p', `翌日へ引継ぎ：${unresolved.items.length}件。確認時刻・影響・次の調査を元データに記録済み。`));
    if (report?.publication_policy?.mode === 'provisional') {
      body.append(el('p', '注釈付き暫定版（MANUAL_REVIEW）。完全版の品質基準は未達です。'));
      for (const item of unresolved?.items || []) {
        const attempts = (item.attempts || []).map(a => `${a.method}：${a.result}（${a.checked_at}）`).join(' / ');
        body.append(el('p', `不足：${item.missing}｜分析への影響：${item.impact}｜実際の確認：${attempts}｜次の対応：${item.next_action}`));
      }
    }

    if (report) {
      const day = report.report_date;
      const context = document.getElementById('report-date');
      if (context) context.textContent = `公開日 ${day}｜市場基準 ${report.target_market_date}`;
      if (!date && report.publication_policy?.mode === 'provisional') {
        const historyState = document.getElementById('history-mode');
        if (historyState) historyState.textContent = `AIレポート：${day}公開済み（注釈付き暫定版）｜市場基準 ${report.target_market_date}`;
      }
      const headings = {
        'quick-view-title': '⚡ 朝3分の要点',
        'quick-conclusion-label': '📌 今日の市場の結論',
        'quick-events-label': '📅 今日の確認項目'
      };
      for (const [id, label] of Object.entries(headings)) {
        const target = document.getElementById(id); if (target) target.textContent = label;
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
  window.addEventListener('publication-data-loaded', render);
  render();
})();
