/* Reader-facing verified news. Audit evidence stays in news.json; presentation metadata is separate. */
(() => {
  const host = document.getElementById('verified-news');
  if (!host) return;

  const page = location.pathname.includes('japan-stocks') ? 'japan' : 'world';
  const otherPage = page === 'world' ? 'japan-stocks.html' : 'index.html';
  const pageTitle = page === 'world' ? '世界市場の重要ニュース' : '日本株の重要ニュース';
  const node = (tag, text, className = '') => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  const safeDate = value => /^20\d{2}-\d{2}-\d{2}$/.test(value || '') ? value : null;
  const safeUrl = value => {
    try { const url = new URL(value); return url.protocol === 'https:' && !url.username ? url.href : null; }
    catch { return null; }
  };
  const readable = (value, max = 1200) => {
    if (typeof value !== 'string') return null;
    const text = value.replace(/\s+/g, ' ').trim();
    if (text.length < 2 || text.length > max) return null;
    if (/�|\[object Object\]|\b(undefined|null|NaN)\b/i.test(text)) return null;
    if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(text)) return null;
    return text;
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

  const japanPublishers = new Set([
    '日本銀行', '総務省統計局', 'OSG', 'イオンフィナンシャルサービス',
    'フジミインコーポレーテッド', '安川電機', 'ジンズホールディングス', 'HOYA'
  ]);
  function inferredPage(article) {
    const title = readable(article.title, 240) || '';
    if (japanPublishers.has(article.publisher)) return 'japan';
    if (/[（(]\d{4}[）)]/.test(title)) return 'japan';
    return 'world';
  }
  function displayMeta(article, config) {
    const configured = config?.items?.[article.id];
    return {
      primary_page: configured?.primary_page === 'japan' || configured?.primary_page === 'world'
        ? configured.primary_page : inferredPage(article),
      priority: Number.isFinite(Number(configured?.priority)) ? Number(configured.priority) : 50,
      impact_summary: readable(configured?.impact_summary, 420) || readable(article.analysis, 420),
      attention_points: Array.isArray(configured?.attention_points)
        ? configured.attention_points.map(item => readable(item, 240)).filter(Boolean).slice(0, 3)
        : []
    };
  }
  function renderArticle(article, meta) {
    const title = readable(article.title, 240);
    const fact = readable(article.fact);
    const source = safeUrl(article.source_url);
    if (!title || !fact || !source) return null;
    const card = node('article', undefined, 'news-card');
    card.append(node('h3', title, 'news-title'));
    const metaLine = node('p', undefined, 'news-meta');
    metaLine.append(node('span', article.published_date, 'news-date'));
    metaLine.append(node('span', article.publisher, 'news-publisher'));
    card.append(metaLine);
    card.append(node('p', fact, 'news-fact'));
    if (meta.impact_summary) {
      const impact = node('div', undefined, 'news-impact');
      impact.append(node('div', page === 'japan' ? '日本株への影響' : 'なぜ重要か', 'news-label'));
      impact.append(node('p', meta.impact_summary));
      card.append(impact);
    }
    if (meta.attention_points.length) {
      const caution = node('div', undefined, 'news-caution');
      caution.append(node('div', '注意点', 'news-label'));
      const list = node('ul');
      meta.attention_points.forEach(item => list.append(node('li', item)));
      caution.append(list); card.append(caution);
    }
    const link = node('a', `出典：${article.publisher} ↗`, 'news-source');
    link.href = source; link.target = '_blank'; link.rel = 'noopener noreferrer';
    card.append(link);
    return card;
  }

  let requestId = 0;
  let lastPageDate = new URLSearchParams(location.search).get('date');
  const indexPromise = read('/data/news-history.json').catch(() => ({dates: []}));
  const configPromise = read('/data/news-display.json').catch(() => ({items: {}}));
  async function render() {
    const sequence = ++requestId;
    const params = new URLSearchParams(location.search);
    const selected = safeDate(params.get('news-date') || params.get('date'));
    const prefix = selected ? `/data/history/${selected}` : '/data';
    host.hidden = false;
    host.replaceChildren(node('h2', pageTitle, 'section-title'));

    const controls = node('div', undefined, 'news-controls');
    const label = node('label', '表示日：');
    const select = document.createElement('select');
    select.id = 'verified-news-date'; select.setAttribute('aria-label', 'ニュースの日付');
    const latest = node('option', '最新'); latest.value = ''; select.append(latest);
    label.append(select); controls.append(label); host.append(controls);
    const loading = node('p', 'ニュースを読み込み中...', 'news-status'); host.append(loading);

    const [index, config] = await Promise.all([indexPromise, configPromise]);
    if (sequence !== requestId) return;
    const dates = [...new Set((index.dates || []).filter(safeDate))].sort().reverse();
    if (selected && !dates.includes(selected)) dates.unshift(selected);
    dates.forEach(day => { const option = node('option', day); option.value = day; select.append(option); });
    select.value = selected || '';
    select.addEventListener('change', () => {
      const url = new URL(location.href);
      if (select.value) url.searchParams.set('news-date', select.value);
      else { url.searchParams.delete('news-date'); if (url.searchParams.has('date')) url.searchParams.set('news-date', 'latest'); }
      history.replaceState(null, '', url); render();
    });

    try {
      const [newsResult, marketResult, reportResult] = await Promise.allSettled([
        read(`${prefix}/news.json`), read(`${prefix}/market.json`), read(`${prefix}/report.json`)
      ]);
      if (sequence !== requestId) return;
      loading.remove();
      if (newsResult.status !== 'fulfilled') throw new Error('news unavailable');
      const news = newsResult.value;
      if (news.publication_mode !== 'verified_news' || !Array.isArray(news.articles) || (selected && news.report_date !== selected)) throw new Error('invalid news');

      const eligible = news.articles
        .filter(article => article.verification_status === 'PASS' && article.source_type === 'primary')
        .map(article => ({article, meta: displayMeta(article, config)}));
      const articles = eligible.filter(item => item.meta.primary_page === page)
        .sort((a, b) => b.meta.priority - a.meta.priority || b.article.published_date.localeCompare(a.article.published_date));
      const otherCount = eligible.length - articles.length;

      const summary = node('div', undefined, 'news-summary');
      summary.append(node('strong', `${news.report_date}更新`));
      summary.append(node('span', `このページ ${articles.length}件`));
      const otherLink = node('a', `${page === 'world' ? '日本株' : '世界市場'} ${otherCount}件`, 'news-other-link');
      otherLink.href = otherPage + (selected ? `?date=${encodeURIComponent(selected)}` : '');
      summary.append(otherLink); host.append(summary);

      const primary = node('div', undefined, 'news-list news-list-primary');
      const secondary = node('div', undefined, 'news-list');
      articles.forEach((item, index) => {
        const card = renderArticle(item.article, item.meta);
        if (card) (index < 6 ? primary : secondary).append(card);
      });
      if (primary.children.length) host.append(primary);
      if (secondary.children.length) {
        const more = node('details', undefined, 'news-more');
        more.append(node('summary', `その他の確認済みニュース（${secondary.children.length}件）`), secondary);
        host.append(more);
      }
      if (!primary.children.length && !secondary.children.length) host.append(node('p', 'このページに掲載する確認済みニュースはありません。', 'news-status'));

      const market = marketResult.status === 'fulfilled' ? marketResult.value : null;
      const report = reportResult.status === 'fulfilled' ? reportResult.value : null;
      const marketDates = [...new Set(Object.values(market?.markets || {}).map(row => row.market_date).filter(Boolean))].sort();
      const quality = node('details', undefined, 'news-quality');
      quality.append(node('summary', 'データ詳細・品質情報'));
      const body = node('div', undefined, 'news-quality-body');
      body.append(node('p', news.coverage_note || '確認済み記事のみを掲載しています。'));
      body.append(node('p', `ニュース確認：${news.updated_at}｜対象市場日：${news.target_market_date}`));
      body.append(node('p', `市場データ基準日：${marketDates.join(' / ') || '確認できず'}｜総合分析：${report?.report_date || '確認できず'}`));
      body.append(node('p', '記事本文の検証証跡・取得履歴・未確認事項は元データに保持しています。'));
      quality.append(body); host.append(quality);
    } catch {
      if (sequence === requestId) {
        loading.remove(); host.append(node('p', selected
          ? `${selected}の確認済みニュースは未保存、または取得できません。最新記事で代替しません。`
          : '確認済みニュースを取得できません。', 'news-status'));
      }
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
