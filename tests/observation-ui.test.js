const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {displaySnapshot, futuresDefined} = require('../assets/market-observation');
test('unknown continuous futures cannot enter prices or rankings; raw data remains intact', () => {
  const raw = {markets: {brent: {price: 104.28, change_pct: 4.07, market_date: '2026-10-08'}, sp500: {price: 7811.54}}};
  const safe = displaySnapshot(raw);
  assert.equal(raw.markets.brent.price, 104.28);
  assert.equal(safe.markets.brent.price, null);
  assert.equal(safe.markets.brent.change_pct, null);
  assert.equal(safe.markets.sp500.price, 7811.54);
});
test('current contract metadata cannot certify a different historical date', () => {
  const row = {market_date:'2026-10-08', instrument: {verification_status:'verified',exchange:'NYMEX',contract_month:'2026-11',value_kind:'daily_close',basis_time:'2026-10-08T17:00:00-04:00',source_url:'https://example.org/report',market_date:'2026-10-09'}};
  assert.equal(futuresDefined(row), false);
  row.instrument.market_date='2026-10-08'; assert.ok(futuresDefined(row));
});
class Element {
  constructor(tag) {this.tag=tag;this.children=[];this.textContent='';}
  append(...nodes) {this.children.push(...nodes);}
  prepend(node) {this.children=this.children.filter(x=>x!==node);this.children.unshift(node);}
  before() {}
  replaceChildren(...nodes) {this.children=nodes;}
  querySelector(selector) {return this.children.find(x=>selector==='.publication-asof' && x.className==='publication-asof') || null;}
}
async function fixture() {
  let day='2026-10-05';
  const ids=new Map(['quick-view','executive-section','report-date'].map(x=>[x,new Element('div')]));
  const handlers={};
  const created=[];
  const context={document:{createElement:t=>{const e=new Element(t);created.push(e);return e;},getElementById:id=>ids.get(id)}, location:{search:''},window:{addEventListener:(name,fn)=>handlers[name]=fn},URLSearchParams,AbortController,setTimeout,clearTimeout,MutationObserver:class {observe(){}},fetch:async path=>{
    if(path.endsWith('market.json')) throw new Error('one network failure');
    const value=path.endsWith('/report.json')?{report_date:day,target_market_date:'2026-10-02',data_quality:{overall:'MANUAL_REVIEW'}}:path.endsWith('/news.json')?{report_date:'2026-10-10',articles:[{}]}:null;
    return {ok:!!value,json:async()=>value};
  }};
  vm.runInNewContext(fs.readFileSync(require.resolve('../assets/publication-health.js'),'utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  return {ids,handlers,created,setDay:x=>day=x};
}
test('one failed fetch cannot erase successful report and news state',async()=>{
  const f=await fixture();
  const host=f.created.find(x=>x.id==='publication-health');
  assert.ok(host.children.some(x=>x.textContent.includes('2026-10-10版・1件')));
  assert.match(f.ids.get('report-date').textContent,/2026-10-05/);
});
test('as-of note updates after date switch rather than remaining stale',async()=>{
  const f=await fixture();
  assert.match(f.ids.get('executive-section').querySelector('.publication-asof').textContent,/2026-10-05/);
  f.setDay('2026-10-09');await f.handlers['publication-data-loaded']();
  assert.match(f.ids.get('executive-section').querySelector('.publication-asof').textContent,/2026-10-09/);
  assert.equal(f.ids.get('executive-section').children.length,1);
});

 test('a missing percentage is never converted to a flat zero move', () => {
 const fs = require('node:fs'); const vm = require('node:vm');
 const source = fs.readFileSync('index.html','utf8');
 const fn = source.slice(source.indexOf('function validChange('), source.indexOf('function average('));
 const context = {}; vm.runInNewContext(fn,context);
 assert.equal(context.validChange({change_pct:null}),null);
 assert.equal(context.validChange({change_pct:0}),0);
 });
