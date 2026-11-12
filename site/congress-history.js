/* Offline Congress history: support among scored members and evidence coverage. */
(function (global) {
  'use strict';
  const names={all:'All members',D:'Democrats',R:'Republicans'}, order=['all','D','R'];
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const percentText=value=>Number.isFinite(value)?`${value.toFixed(1)}%`:'Unavailable';
  function series(history,congress,dimension) {
    return history.filter(r=>r.c===congress && r.k===dimension && names[r.p] && Number.isFinite(Date.parse(r.d+'T00:00:00Z')))
      .map(r=>{
        const valid=[r.n,r.scored,r.hi].every(n=>Number.isInteger(n)&&n>=0) && r.hi<=r.scored && r.scored<=r.n;
        return {...r,who:names[r.p],scored:valid?r.scored:null,
          percent:valid&&r.scored>0?r.hi/r.scored*100:null,
          coveragePercent:valid&&r.n>0?r.scored/r.n*100:null};
      }).sort((a,b)=>order.indexOf(a.p)-order.indexOf(b.p)||a.d.localeCompare(b.d));
  }
  const supportText=row=>row.scored===0?'No scored members':percentText(row.percent);
  function details(rows) {
    if (!rows.length) return '';
    const latest=new Map();
    for (const row of rows) if (!latest.has(row.p)||row.d>latest.get(row.p).d) latest.set(row.p,row);
    const table=items=>`<div class="trend-counts"><table><thead><tr><th scope="col">Date</th><th scope="col">Group</th><th scope="col">Share among scored</th><th scope="col">Evidence coverage</th></tr></thead><tbody>${items.map(r=>`<tr><th scope="row">${esc(r.d)}</th><td>${esc(r.who)}</td><td>${supportText(r)}${r.scored!==null?`<small>${r.hi} of ${r.scored} scored members</small>`:''}</td><td>${percentText(r.coveragePercent)}${r.scored!==null?`<small>${r.scored} of ${r.n} members</small>`:''}</td></tr>`).join('')}</tbody></table></div>`;
    return `<p class="note"><strong>Latest counts</strong> · Scores of 3 or higher among scored members.</p>${table([...latest.values()])}
      <details class="trend-history"><summary>Exact dates and counts (${rows.length})</summary>${table([...rows].sort((a,b)=>b.d.localeCompare(a.d)||order.indexOf(a.p)-order.indexOf(b.p)))}</details>`;
  }
  const api={series,details,percentText,supportText};
  if (typeof module!=='undefined'&&module.exports) module.exports=api; else global.CongressHistory=api;
})(typeof window!=='undefined'?window:globalThis);
