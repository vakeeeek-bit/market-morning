/* Independent fact-only news feed. Market and narrative report retain their own dates. */
(async () => {
  const host = document.getElementById('verified-news');
  if (!host) return;
  const syncHistory = () => {
    host.hidden = new URLSearchParams(location.search).has('date');
  };
  syncHistory();
  const historyMode = document.getElementById('history-mode');
  if (historyMode) new MutationObserver(syncHistory).observe(historyMode, {childList: true});
  window.addEventListener('popstate', syncHistory);
  const node = (tag, content) => {
    const el = document.createElement(tag);
    el.textContent = content;
    return el;
  };
  const read = async path => {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) throw new Error('fetch failed');
    return response.json();
  };
  const safeUrl = value => {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && !url.username ? url.href : null;
    } catch { return null; }
  };
  try {
    const [newsResult, marketResult, reportResult] = await Promise.allSettled([
      read('/data/news.json'), read('/data/market.json'), read('/data/report.json')
    ]);
    if (newsResult.status !== 'fulfilled') throw new Error('news unavailable');
    const news = newsResult.value;
    if (news.publication_mode !== 'verified_news' || !Array.isArray(news.articles)) throw new Error('invalid news');
    host.replaceChildren(node('h2', '確認済みニュース'));
    const today = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Tokyo'}).format(new Date());
    host.append(node('p', `ニュース更新日：${news.report_date}｜${news.report_date === today ? '本日更新' : '過去の更新（本日分ではありません）'}｜${news.updated_at}`));
    const market = marketResult.status === 'fulfilled' ? marketResult.value : null;
    const observations = Object.values(market?.markets || {});
    const dates = [...new Set(observations.map(row => row.market_date).filter(Boolean))].sort();
    const report = reportResult.status === 'fulfilled' ? reportResult.value : null;
    const current = dates.length === 1 && dates[0] === news.target_market_date;
    host.append(node('p', `市場データ：${!market ? '取得不可' : current ? '対象日が一致' : '一部未更新・基準日混在'}｜基準日：${dates.join(' / ') || '不明'}｜レポート日：${report?.report_date || '取得不可'}`));
    host.append(node('p', 'ニュースの確認状態と市場・総合レポートの品質判定は別です。'));
    host.append(node('p', news.coverage_note || '確認済み記事のみ。調査は部分的です。'));
    for (const article of news.articles) {
      if (article.verification_status !== 'PASS' || article.source_type !== 'primary') continue;
      const source = safeUrl(article.source_url);
      if (!source) continue;
      const card = document.createElement('article');
      card.className = 'card';
      card.append(node('h3', article.title));
      card.append(node('p', `発表日：${article.published_date}｜確認：${article.verified_at}`));
      card.append(node('p', `事実：${article.fact}`));
      card.append(node('p', `解釈：${article.analysis}`));
      card.append(node('p', `留保：${article.limitations}｜市場反応：未確認`));
      const link = node('a', `出典：${article.publisher}`);
      link.href = source;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      card.append(link);
      host.append(card);
    }
  } catch {
    host.replaceChildren(node('p', '確認済みニュースを取得できません。市場・レポートはそれぞれの更新日を確認してください。'));
  }
})();
