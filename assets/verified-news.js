/* Independent verified news: live feed and explicitly retrospective archives. */
(() => {
  const host = document.getElementById('verified-news');
  if (!host) return;
  const node = (tag, text) => { const el = document.createElement(tag); el.textContent = text; return el; };
  const safeDate = value => /^20\d{2}-\d{2}-\d{2}$/.test(value || '') ? value : null;
  const safeUrl = value => {
    try { const u = new URL(value); return u.protocol === 'https:' && !u.username ? u.href : null; }
    catch { return null; }
  };
  const read = async path => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(path, {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new Error('fetch failed');
      return await response.json();
    } finally { clearTimeout(timer); }
  };
  let requestId = 0;
  let lastPageDate = new URLSearchParams(location.search).get('date');
  const indexPromise = read('/data/news-history.json').catch(() => ({dates: []}));
  async function render() {
    const sequence = ++requestId;
    const params = new URLSearchParams(location.search);
    const selected = safeDate(params.get('news-date') || params.get('date'));
    const prefix = selected ? `/data/history/${selected}` : '/data';
    host.hidden = false;
    host.replaceChildren(node('h2', '確認済みニュース'));
    const label = node('label', 'ニュースの日付：');
    const select = document.createElement('select');
    select.id = 'verified-news-date';
    select.setAttribute('aria-label', 'ニュースの日付');
    const latest = node('option', '最新ニュース'); latest.value = ''; select.append(latest);
    label.append(select); host.append(label);
    const loading = node('p', 'ニュースを読み込み中...'); host.append(loading);
    const index = await indexPromise;
    if (sequence !== requestId) return;
    const dates = [...new Set((index.dates || []).filter(safeDate))].sort().reverse();
    if (selected && !dates.includes(selected)) dates.unshift(selected);
    for (const day of dates) { const option = node('option', day); option.value = day; select.append(option); }
    select.value = selected || '';
    select.addEventListener('change', () => {
      const url = new URL(location.href);
      if (select.value) url.searchParams.set('news-date', select.value);
      else { url.searchParams.delete('news-date'); if (url.searchParams.has('date')) url.searchParams.set('news-date', 'latest'); }
      history.replaceState(null, '', url); render();
    });
    try {
      const [n, m, r] = await Promise.allSettled([read(`${prefix}/news.json`), read(`${prefix}/market.json`), read(`${prefix}/report.json`)]);
      if (sequence !== requestId) return;
      loading.remove();
      if (n.status !== 'fulfilled') throw new Error('news unavailable');
      const news = n.value;
      if (news.publication_mode !== 'verified_news' || !Array.isArray(news.articles) || (selected && news.report_date !== selected)) throw new Error('invalid news');
      const today = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Tokyo'}).format(new Date());
      host.append(node('p', news.edition === 'retrospective'
        ? `ニュース対象日：${news.report_date}｜後日収集：${news.collected_at}｜当日朝の調査・公開記録ではありません`
        : `ニュース更新日：${news.report_date}｜${news.report_date === today ? '本日更新' : '過去の更新（本日分ではありません）'}｜${news.updated_at}`));
      const market = m.status === 'fulfilled' ? m.value : null;
      const marketDates = [...new Set(Object.values(market?.markets || {}).map(row => row.market_date).filter(Boolean))].sort();
      const report = r.status === 'fulfilled' ? r.value : null;
      const current = marketDates.length === 1 && marketDates[0] === news.target_market_date;
      host.append(node('p', `市場データ：${!market ? '取得不可・未保存' : current ? '対象日が一致' : '一部未更新・基準日混在'}｜基準日：${marketDates.join(' / ') || '不明'}｜総合レポート日：${report?.report_date || '未保存'}`));
      host.append(node('p', 'ニュースの確認状態と市場・総合レポートの品質判定は別です。'));
      host.append(node('p', news.coverage_note || '確認済み記事のみ。調査は部分的です。'));
      for (const article of news.articles) {
        if (article.verification_status !== 'PASS' || article.source_type !== 'primary') continue;
        const source = safeUrl(article.source_url); if (!source) continue;
        const card = document.createElement('article'); card.className = 'card';
        card.append(node('h3', article.title), node('p', `発表日：${article.published_date}｜確認：${article.verified_at}`));
        card.append(node('p', `事実：${article.fact}`), node('p', `解釈：${article.analysis}`));
        card.append(node('p', `留保：${article.limitations}｜市場反応：未確認`));
        const link = node('a', `出典：${article.publisher}`); link.href = source; link.target = '_blank'; link.rel = 'noopener noreferrer';
        card.append(link); host.append(card);
      }
    } catch {
      if (sequence === requestId) { loading.remove(); host.append(node('p', selected
        ? `${selected}の確認済みニュースは未保存、または取得できません。最新記事で代替しません。`
        : '確認済みニュースを取得できません。各データの更新日を確認してください。')); }
    }
  }
  const historyMode = document.getElementById('history-mode');
  if (historyMode) new MutationObserver(() => {
    const current = new URLSearchParams(location.search).get('date');
    if (current !== lastPageDate) {
      lastPageDate = current;
      const url = new URL(location.href); url.searchParams.delete('news-date'); history.replaceState(null, '', url); render();
    }
  }).observe(historyMode, {childList: true});
  window.addEventListener('popstate', render);
  render();
})();
