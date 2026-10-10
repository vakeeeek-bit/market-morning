/* Keep raw snapshots intact; only defined observations enter price displays. */
(function (root) {
  const futures = new Set(['gold', 'silver', 'copper', 'wti', 'brent']);
  function futuresDefined(row) {
    const i = row?.instrument || {};
    return i.verification_status === 'verified' &&
      /^20\d{2}-(0[1-9]|1[0-2])$/.test(i.contract_month || '') &&
      typeof i.exchange === 'string' && i.exchange.trim() &&
      ['daily_close', 'settlement', 'current'].includes(i.value_kind) &&
      typeof i.basis_time === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(i.basis_time) && !Number.isNaN(Date.parse(i.basis_time)) &&
      /^https:\/\//.test(i.source_url || '') && i.market_date === row.market_date;
  }
  function displaySnapshot(data) {
    const markets = Object.fromEntries(Object.entries(data.markets || {}).map(([key, row]) => {
      if (!futures.has(key) || futuresDefined(row)) return [key, {...row}];
      return [key, {...row, price: null, change: null, change_pct: null,
        status: '確認できず', display_note: '限月・値種別・基準時刻の確認不足：数値表示を控えています'}];
    }));
    return {...data, markets};
  }
  const api = {futuresDefined, displaySnapshot};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MarketObservation = api;
})(typeof window === 'undefined' ? {} : window);
