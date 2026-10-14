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
  appendChild(node) {this.children.push(node);return node;}
  prepend(node) {this.children=this.children.filter(x=>x!==node);this.children.unshift(node);}
  before() {}
  replaceChildren(...nodes) {this.children=nodes;}
  querySelector(selector) {return this.children.find(x=>selector==='.publication-asof' && x.className==='publication-asof') || null;}
}
test('formal report quality fields display limitations instead of false none', () => {
  const source=fs.readFileSync('index.html','utf8');
  const start=source.indexOf('function renderQuality(');
  const end=source.indexOf('\nfunction ',start+1);
  const ids=new Map(['quality-grade','quality-detail'].map(id=>[id,new Element('div')]));
  const context={document:{getElementById:id=>ids.get(id),createElement:t=>new Element(t)},clearElement:e=>e.replaceChildren(),safeText:(x,f)=>x||f};
  vm.runInNewContext(source.slice(start,end),context);
  context.renderQuality({overall:'MANUAL_REVIEW',missing:['当日市場値未取得'],differences:['基準日が異なる'],cautions:['部分収集'],excluded:['限月不明の先物']});
  assert.equal(ids.get('quality-grade').textContent,'MANUAL_REVIEW');
  const strings=[];const visit=e=>{strings.push(e.textContent);e.children.forEach(visit);};visit(ids.get('quality-detail'));
  for(const text of ['当日市場値未取得','基準日が異なる','部分収集','限月不明の先物']) assert.ok(strings.includes(text));
  assert.ok(!strings.includes('なし'));
});
async function fixture(options={}) {
  let day='2026-10-05';
  const ids=new Map(['quick-view','executive-section','report-date','quality-section'].map(x=>[x,new Element('div')]));
  const handlers={};
  const created=[];
  const context={document:{createElement:t=>{const e=new Element(t);created.push(e);return e;},getElementById:id=>ids.get(id)}, location:{search:''},window:{addEventListener:(name,fn)=>handlers[name]=fn},URLSearchParams,AbortController,setTimeout,clearTimeout,MutationObserver:class {observe(){}},fetch:async path=>{
    if(path.endsWith('market.json')) throw new Error('one network failure');
    const value=path.endsWith('/report.json')?{report_date:day,target_market_date:'2026-10-02',updated_at:options.reportUpdatedAt,data_quality:{overall:'MANUAL_REVIEW'}}:path.endsWith('/news.json')?{report_date:'2026-10-10',articles:[{}]}:path.endsWith('/site-audit.json')?options.audit:null;
    return {ok:!!value,json:async()=>value};
  }};
  vm.runInNewContext(fs.readFileSync(require.resolve('../assets/publication-health.js'),'utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  return {ids,handlers,created,setDay:x=>day=x};
}
test('one failed fetch cannot erase successful report and news state',async()=>{
  const f=await fixture();
  const host=f.created.find(x=>x.id==='publication-health');
  const body=host.children.find(x=>x.className==='disclosure-body publication-health-body');
  assert.ok(body.children.some(x=>x.children?.some?.(item=>item.textContent.includes('2026-10-10版｜1件'))));
  assert.match(f.ids.get('report-date').textContent,/2026-10-05/);
});
test('date switch updates one concise header without repeating as-of notes',async()=>{
  const f=await fixture();
  assert.match(f.ids.get('report-date').textContent,/2026-10-05/);
  f.setDay('2026-10-09');await f.handlers['publication-data-loaded']();
  assert.match(f.ids.get('report-date').textContent,/2026-10-09/);
  assert.equal(f.ids.get('executive-section').children.length,0);
});

test('a candidate audit older than the published report is not displayed',async()=>{
  const f=await fixture({
    reportUpdatedAt:'2026-10-12T16:41:41+09:00',
    audit:{checked_at:'2026-10-12T13:50:45+09:00',report_publication_status:'午後候補：未公開',blockers:[]}
  });
  const host=f.created.find(x=>x.id==='publication-health');
  const body=host.children.find(x=>x.className==='disclosure-body publication-health-body');
  assert.ok(!body.children.some(x=>x.textContent.includes('午後候補：未公開')));
});

test('an audit newer than the published report remains visible',async()=>{
  const f=await fixture({
    reportUpdatedAt:'2026-10-12T16:41:41+09:00',
    audit:{checked_at:'2026-10-12T17:00:00+09:00',report_publication_status:'再点検中',blockers:[]}
  });
  const host=f.created.find(x=>x.id==='publication-health');
  const body=host.children.find(x=>x.className==='disclosure-body publication-health-body');
  assert.ok(body.children.some(x=>x.textContent.includes('再点検中')));
});

 test('a missing percentage is never converted to a flat zero move', () => {
 const fs = require('node:fs'); const vm = require('node:vm');
 const source = fs.readFileSync('index.html','utf8');
 const fn = source.slice(source.indexOf('function validChange('), source.indexOf('function average('));
 const context = {}; vm.runInNewContext(fn,context);
 assert.equal(context.validChange({change_pct:null}),null);
 assert.equal(context.validChange({change_pct:0}),0);
 });
