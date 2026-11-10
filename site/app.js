const DIMS = [
  ["ai_overall","AI overall","from a threat to enthusiastic","are mostly optimistic about AI"],
  ["agi_pilled","AGI-pilled","from dismisses AGI to thinks AGI is near","see AGI as a real possibility"],
  ["x_risk","AI x-risk","from dismisses AI x-risk to a top priority","want action on catastrophic AI risk"],
  ["china_race","China race","from rejects the race to outweighs all else","make the China race a main reason for their AI positions"],
  ["regulation","Regulation","from opposes AI rules to comprehensive rules","back substantial rules on AI companies"],
];
const TOPICS = ["jobs/economy","China/competition","national security","kids/online safety","deepfakes/elections","copyright","energy/data centers","regulation","AGI/transformative","x-risk/loss of control","misuse (bio/cyber)","other"];
// each level says what the member does, so it reads on its own without the 0-4 number
const LEVELS = {
  ai_overall:["Sees AI mainly as a threat","Sees more harm than good","Weighs harm and good equally","Sees AI mainly as an opportunity","Enthusiastic about AI"],
  agi_pilled:["Dismisses AGI","Sees AI as ordinary technology","Expects very large change","Thinks AGI is possible","Thinks AGI is near"],
  x_risk:["Dismisses AI x-risk","Mentions x-risk, plays it down","Calls x-risk a real risk","Wants action on x-risk","Calls x-risk a top priority"],
  china_race:["Rejects the China race","Mentions the China race","China race is one reason","China race is the main reason","China race outweighs all else"],
  regulation:["Opposes AI rules","Wants light-touch rules","Wants targeted rules","Wants substantial rules","Wants comprehensive rules"],
};
// a half score means the two models were one level apart
function levelText(k, v){ if (v==null) return "Not enough evidence"; if (v===Math.floor(v)) return LEVELS[k][v];
  const lo=Math.floor(v); return `Between “${LEVELS[k][lo]}” and “${LEVELS[k][lo+1]}”`; }
const PNAME = {D:"Democrats",R:"Republicans",I:"Independents"};
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const PC = p => css(p==="D"?"--pD":p==="R"?"--pR":"--pI");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let FED = null, M = [], TL = [], COMM = {}, UPDATED = "", DAILY = null, HISTORY = null, CHANGES = null, RF = null, rfSel = null;
const S = {cong:"119", party:"all", dim:"x_risk", preset:null, range:"365", events:false, who:"congress"};   // range: topic chart window in days
let sortKey = "n", sortDir = -1, open = null;

/* ---------- helpers ---------- */
function inCong(m, c=S.cong){ return c==="119" ? m.status==="current" : (m.next==="continuing"||m.next==="arriving"); }
function chamberOf(m, c=S.cong){ return c==="119" ? m.chamber : m.next_chamber; }
const GROUPS_IN = c => c==="119" ? new Set(["continuing","departing","pending"]) : new Set(["continuing","arriving"]);
function partyOk(m){ return S.party==="all" || m.party===S.party; }
function seat(m){ return m.chamber==="senate" ? `${m.state}` : `${m.state}-${(m.district===0||m.district==="0"||m.district==null)?"AL":m.district}`; }
function clean(t){ return String(t??"").replace(/\s*\((?:s\d+(?:\s*[,;–-]\s*|\s+and\s+)?)+\)/g,"").replace(/\bs\d+\b,?\s*/g,"").replace(/\s{2,}/g," "); }
function fmt(v){ return v==null ? "—" : (Math.round(v*10)/10).toString(); }
function hash(s){let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))|0;return ((h>>>0)%1000)/1000;}
function ramp(){ return [0,1,2,3,4].map(i=>css("--r"+i)); }
function scoreColor(v){ if(v==null) return css("--nodata"); const r=ramp(); const lo=Math.floor(v), hi=Math.min(4,lo+1); return lo===hi?r[lo]:d3.interpolateLab(r[lo],r[hi])(v-lo); }
function dimLabel(k=S.dim){ return DIMS.find(d=>d[0]===k)[1]; }
function plotStyle(){ return {background:"transparent",fontSize:"11px",color:css("--fg")}; }
function widthOf(el){ return Math.max(300, el.clientWidth-24); }
const tip = document.getElementById("tip");
function showTip(e, html){ tip.style.display="block"; tip.innerHTML=html; const w=tip.offsetWidth; tip.style.left=Math.min(e.clientX+14, innerWidth-w-8)+"px"; tip.style.top=Math.min(e.clientY+14, innerHeight-tip.offsetHeight-8)+"px"; }
function hideTip(){ tip.style.display="none"; }
function memberTip(m, k=S.dim){ return `<b class="p${m.party}">${esc(m.name)}</b> (${m.party}-${seat(m)})${m.status==="member_elect"?' · <i>new member</i>':m.next==="departing"?' · <i>leaving</i>':""}<br>${dimLabel(k)}: <b>${esc(levelText(k, m.scores[k]))}</b> · ${m.n} statements<br><span class="note">${esc((m.summary||"Not enough public statements about AI to summarize.").slice(0,260))}${(m.summary||"").length>260?"…":""}</span>`; }
function setTitle(id, t){ const h=document.getElementById(id); if (h.firstChild && h.firstChild.nodeType===3) h.firstChild.nodeValue=t; else h.prepend(t); }  // keeps the Cite button
function goMember(m){ if (!$("tbl")) { location.href = "index.html#member-" + m.id; return; } document.getElementById("q").value=m.name; document.getElementById("fst").value=""; renderTable(); openRow(m.id); document.getElementById("members").scrollIntoView({behavior:"smooth"}); }
function bindHover(nodes, data, html, click){
  [...nodes].forEach((n,i)=>{ const d=data[i]; if(d===undefined) return; n.classList.add("hit");
    n.onmousemove=e=>showTip(e,html(d)); n.onmouseleave=hideTip; n.onclick=()=>{hideTip(); click&&click(d);}; });
}
const SHORT = {ai_overall:"overall", agi_pilled:"AGI", x_risk:"x-risk", china_race:"China", regulation:"regulation"};
function labChips(q){ const by=(q.by||["Claude","GPT"]).join(" / "); return Object.entries(q.lab||{}).map(([k,v])=>`<span class="chip" title="Level this statement shows on ${esc(dimLabel(k))} (${esc(by)})" style="border:1px solid var(--line)">${SHORT[k]} ${v.map(x=>x??"–").join("/")}</span>`).join(""); }
function legendHTML(items){ return items.map(([lab,col,cls])=>`<span><i class="${cls||""}" style="background:${col}"></i>${esc(lab)}</span>`).join(""); }

/* ---------- init ---------- */
const $ = id => document.getElementById(id);
async function init(){
  const [mj, tl, cm] = await Promise.all(["members","timeline","committees"].map(f=>fetch(`data/${f}.json`).then(r=>r.json())));
  M = mj.members; TL = tl; COMM = cm; UPDATED = mj.updated;
  const opt = f => fetch(`data/${f}.json`).then(r=>r.ok?r.json():null).catch(()=>null);
  [DAILY, HISTORY, CHANGES, RF] = await Promise.all([opt("daily"), opt("history"), opt("changes"), opt("regfocus")]);
  if ($("rfchart") && document.querySelector("[data-who]")) FED = await opt("federal_analysis");
  // Policies page: Congress / Executive officials / Institutions switch drives both charts
  document.querySelectorAll("[data-who]").forEach(b=>b.onclick=()=>{ S.who=b.dataset.who; rfSel=null;
    document.querySelectorAll("[data-who]").forEach(x=>x.setAttribute("aria-checked", x.dataset.who===S.who));
    if ($("congsel")) $("congsel").hidden = S.who!=="congress";
    keepPlace(()=>{ drawRegFocus(); dispatchEvent(new CustomEvent("policyscope",{detail:S.who})); }); });
  if ($("updated")) $("updated").textContent = mj.updated;
  if ($("nmembers")) $("nmembers").textContent = M.length.toLocaleString();
  if ($("nquotes")) $("nquotes").textContent = M.reduce((a,m)=>a+m.n,0).toLocaleString();
  if ($("dimsel")){ dimsel.innerHTML = DIMS.map(([k,l])=>`<option value="${k}">${l}</option>`).join(""); dimsel.value = S.dim;
    dimsel.onchange = ()=>{ S.dim = dimsel.value; drawAll(); }; }
  const evt = $("evtoggle");
  if (evt) evt.onclick = ()=>{ S.events = !S.events; evt.setAttribute("aria-checked", S.events); keepPlace(()=>{ drawTrend(); drawFocus(); }); };
  document.querySelectorAll("[data-cong]").forEach(b=>b.onclick=()=>{ S.cong=b.dataset.cong;
    document.querySelectorAll("[data-cong]").forEach(x=>x.setAttribute("aria-checked", x.dataset.cong===S.cong)); drawAll(); });
  if ($("tbl")){ ["q","fch","fpa","fst","fev"].forEach(id=>$(id).oninput=renderTable); renderHead(); renderTable(); }
  if ($("presets")) drawPresets();
  drawAll();
  let t; addEventListener("resize", ()=>{clearTimeout(t); t=setTimeout(drawAll,150);});
}
// line up the Key events switch with the right edge of the content under the bar: the charts' common right edge
// (they are drawn 24px inside the content box, see widthOf) or the pies, whichever is further left
function alignEvToggle(){
  const t = document.getElementById("evtoggle"), pie = document.querySelector("#pies svg"), bar = t.parentElement;
  const edge = bar.getBoundingClientRect().right - parseFloat(getComputedStyle(bar).paddingRight);
  let target = edge - 24;
  if (pie && innerWidth > 720) target = Math.min(target, pie.getBoundingClientRect().right);   // narrow screens: pies wrap into a centered row
  t.style.marginRight = Math.max(0, Math.round(edge - target - 4)) + "px";   // 4px = button padding
}
// keep the reader's place: remember where the heading nearest the top of the view sits, redraw, then scroll back
function keepPlace(fn){
  const hs = [...document.querySelectorAll("main h2[id], main h3[id]")];
  const anchor = hs.filter(h=>h.getBoundingClientRect().top <= innerHeight*0.4).pop();
  const before = anchor && anchor.getBoundingClientRect().top;
  fn();
  if (anchor) { const d = anchor.getBoundingClientRect().top - before; if (Math.abs(d) > 1) scrollBy({top:d, behavior:"instant"}); }
}
function drawAll(){ keepPlace(drawCharts); }
function drawCharts(){
  const d = DIMS.find(x=>x[0]===S.dim);
  document.querySelectorAll(".dimname").forEach(e=>e.textContent=d[1]);
  // each page has only some of the charts; draw the ones whose container is on this page
  [["hemi",drawHemis],["evtoggle",alignEvToggle],["ideo",drawIdeology],["partydist",drawPartyDist],["trend",drawTrend],["changelist",drawChanges],
   ["rfchart",drawRegFocus],["focuschart",drawFocus],["voices",drawVoices],["list-names",drawList],["comm",drawComm]].forEach(([id,f])=>{ if ($(id)) f(); });
}
// three states used by the seat chart and the committee bars
// plain words for "scores 3 or more" and "scores 0 to 2" on each question
const SIDE = {
  ai_overall:["Optimistic about AI","Wary or mixed on AI"],
  agi_pilled:["Expects AGI","Doesn't expect AGI"],
  x_risk:["Wants action on AI x-risk","Doesn't prioritize AI x-risk"],
  china_race:["China race drives their AI views","China race is a minor factor"],
  regulation:["Wants substantial AI rules","Wants few or targeted rules"],
};
const STATES = [["yes","","--yes"],["no","","--no"],["none","Hasn't said enough","--card"]];
const stateLabel = (st, k=S.dim) => st==="yes" ? SIDE[k][0] : st==="no" ? SIDE[k][1] : "Hasn't said enough";
const stateOf = (m,k=S.dim) => m.scores[k]==null ? "none" : m.scores[k]>=3 ? "yes" : "no";
function stateLegend(){ return `<span><i class="dot" style="background:${css("--yes")}"></i>${esc(SIDE[S.dim][0])}</span><span><i class="dot" style="background:${css("--no")}"></i>${esc(SIDE[S.dim][1])}</span><span><i class="ring"></i>Hasn't said enough</span>`; }

/* ---------- seating chart ---------- */
function hemiLayout(n, rows){
  const r0 = 0.38, radii = d3.range(rows).map(i=> r0 + (1-r0)*i/(rows-1));
  const tot = d3.sum(radii); let per = radii.map(r=>Math.round(n*r/tot));
  let diff = n - d3.sum(per); for (let i=rows-1; diff!==0; i=(i-1+rows)%rows){ per[i]+=Math.sign(diff); diff-=Math.sign(diff); }
  const seats = [];
  radii.forEach((r,i)=>{ const k=per[i]; for(let j=0;j<k;j++){ const th = k===1?Math.PI/2:Math.PI*(1-j/(k-1)); seats.push({r,th,x:r*Math.cos(th),y:r*Math.sin(th)}); }});
  seats.sort((a,b)=> (b.th-a.th) || (a.r-b.r));
  const spacing = Math.min((1-r0)/(rows-1), Math.PI/(per[rows-1]-1 || 1));
  return {seats, dot: spacing*0.42};
}
function drawHemis(){
  const k=S.dim, d=DIMS.find(x=>x[0]===k);
  const lvl = m => m.scores[k]==null ? -1 : Math.floor(m.scores[k]+0.5);   // averaged scores like 2.5 round up
  const el = document.getElementById("hemi"); el.innerHTML="";
  const W = Math.min(760, widthOf(el));
  const Rh = W/2 - 4, Rs = Rh*0.6;
  const nS = M.filter(m=>inCong(m) && chamberOf(m)==="senate").length, nH = M.filter(m=>inCong(m) && chamberOf(m)==="house").length;
  const dS = hemiLayout(nS,5).dot*Rs, dH = hemiLayout(nH,11).dot*Rh;
  // flat edges: Senate seats sit on ySen, House seats hang from yHouse, with a small band between
  const cx = W/2, ySen = Rs + 2, yHouse = ySen + dS + dH + 16, H = yHouse + Rh + 4;
  const svg = d3.select(el).append("svg").attr("viewBox",`0 0 ${W} ${H}`).attr("width",W).attr("height",H).attr("role","img")
    .attr("aria-label",`Senate and House seats, ordered and colored by ${d[1]} score`);
  const all = [];
  for (const ch of ["senate","house"]){
    // left to right: not enough evidence, then score 0 up to 4
    const order = M.filter(m=>inCong(m) && chamberOf(m)===ch).sort((a,b)=>lvl(a)-lvl(b) || (a.scores[k]??0)-(b.scores[k]??0) || a.name.localeCompare(b.name));
    all.push(...order);
    const slots = order, {seats, dot} = hemiLayout(order.length, ch==="senate" ? 5 : 11);
    const Rad = ch==="senate" ? Rs : Rh, R = dot*Rad;
    const Rp = Rad - R;   // keep whole dots inside the frame
    const px = s => cx + s.x*Rp, py = s => ch==="senate" ? ySen - s.y*Rp : yHouse + s.y*Rp;
    svg.append("g").selectAll("circle").data(slots.map((m,i)=>({m, s:seats[i]})).filter(x=>x.m)).join("circle")
      .attr("cx",x=>px(x.s)).attr("cy",x=>py(x.s)).attr("r",x=>lvl(x.m)<0?R-0.75:R)
      .attr("fill",x=>lvl(x.m)<0?"none":css("--r"+lvl(x.m)))
      .attr("stroke",x=>lvl(x.m)<0?css("--muted"):"none").attr("stroke-width",1.2).classed("hit",true)
      .on("mousemove",(e,x)=>showTip(e, memberTip(x.m))).on("mouseleave",hideTip).on("click",(e,x)=>{hideTip(); goMember(x.m);});
    // chamber name sits in the empty center of its own half
    const ly = ch==="senate" ? ySen - Rad*0.14 : yHouse + Rad*0.18;
    svg.append("text").attr("x",cx).attr("y",ly).attr("text-anchor","middle").attr("fill",css("--fg")).attr("font-size",15).attr("font-weight",600).text(ch==="senate"?"Senate":"House");
    svg.append("text").attr("x",cx).attr("y",ly+17).attr("text-anchor","middle").attr("fill",css("--muted")).attr("font-size",12).text(`${order.length} seats`);
  }
  setTitle("chamber", `Congress by ${d[1]} score`);
  document.getElementById("hemi-sub").textContent = `Each dot is one seat in ${S.cong==="119"?"the 119th Congress (today)":"the 120th Congress, which starts in January 2027"}, from the lowest score on the left to the highest on the right.`;
  const cnt = v => all.filter(m=>lvl(m)===v).length;
  drawPies(all, lvl);
  document.getElementById("seat-legend").innerHTML =
    `<span><i class="ring"></i>Not enough evidence: <b>${cnt(-1)}</b></span>` +
    [0,1,2,3,4].map(v=>`<span><i class="dot" style="background:${css("--r"+v)}"></i>${LEVELS[k][v]}: <b>${cnt(v)}</b></span>`).join("");
  const pend = M.filter(m=>m.next==="pending").length;
  }

/* ---------- pies: same counts as the seat chart, one per chamber ---------- */
function drawPies(all, lvl){
  const box = document.getElementById("pies"); box.innerHTML = "";
  const k = S.dim, levels = [-1,0,1,2,3,4];
  const color = v => v<0 ? css("--nodata") : css("--r"+v);
  const name = v => v<0 ? "Not enough evidence" : LEVELS[k][v];
  const R = 74;
  for (const ch of ["senate","house"]){
    const xs = all.filter(m=>chamberOf(m)===ch), n = xs.length;
    const data = levels.map(v=>({v, c: xs.filter(m=>lvl(m)===v).length})).filter(d=>d.c>0);
    const hi = xs.filter(m=>lvl(m)>=3).length;
    const wrap = document.createElement("div"); wrap.className = "pie";
    wrap.innerHTML = `<h4>${ch==="senate"?"Senate":"House"}</h4>`;
    box.append(wrap);
    const svg = d3.select(wrap).append("svg").attr("viewBox",`${-R-2} ${-R-2} ${2*R+4} ${2*R+4}`).attr("width",2*R+4).attr("height",2*R+4)
      .attr("role","img").attr("aria-label",`${ch}: ${data.map(d=>`${name(d.v)} ${d.c}`).join(", ")}`);
    const arcs = d3.pie().sort(null).value(d=>d.c)(data);
    svg.selectAll("path").data(arcs).join("path").attr("d", d3.arc().innerRadius(0).outerRadius(R))
      .attr("fill", a=>color(a.data.v)).attr("stroke", css("--bg")).attr("stroke-width", 1.5).classed("hit", true)
      .on("mousemove",(e,a)=>showTip(e, `<b>${ch==="senate"?"Senate":"House"}</b><br>${esc(name(a.data.v))}: <b>${a.data.c}</b> of ${n} seats (${Math.round(a.data.c/n*100)}%)`))
      .on("mouseleave", hideTip);
    const cap = document.createElement("div"); cap.className = "cap";
    cap.textContent = `${Math.round(hi/n*100)}% ${SIDE[k][0].charAt(0).toLowerCase()+SIDE[k][0].slice(1)}`;
    wrap.append(cap);
  }
}

/* ---------- ideology scatter (the original chart format) ---------- */
function drawIdeology(){
  const k=S.dim, d=DIMS.find(x=>x[0]===k), el=document.getElementById("ideo"); el.innerHTML="";
  const data = M.filter(m=>inCong(m) && m.ideology!=null && m.scores[k]!=null).map(m=>({m, x:m.ideology, y:m.scores[k]+(hash(m.id)-.5)*0.4}));
  const W=widthOf(el);
  setTitle("ideo-title", `Ideology and ${d[1]} score`);
  const svg = Plot.plot({width:W, height:420, marginLeft:170, marginBottom:46, marginTop:24, style:plotStyle(),
    x:{label:"Ideology (0 = progressive, 1 = conservative) →", domain:[-0.02,1.02], labelAnchor:"center", labelOffset:38, grid:true},
    y:{label:`↑ ${d[1]} score`, domain:[-0.4,4.4], ticks:[0,1,2,3,4], tickFormat:v=>LEVELS[k][v], grid:true},
    marks:[Plot.dot(data,{x:"x", y:"y", r:5, fill:p=>PC(p.m.party), fillOpacity:.85, stroke:css("--card"), strokeWidth:1}),
]});
  svg.style.overflow="visible";
  el.append(svg);
  bindHover(svg.querySelectorAll("g[aria-label=dot] circle"), data, p=>memberTip(p.m), p=>goMember(p.m));
  document.getElementById("ideo-legend").innerHTML = legendHTML([["Democrat",PC("D"),"dot"],["Republican",PC("R"),"dot"],["Independent",PC("I"),"dot"]]) + `<span>n = ${data.length}</span>`;
}

/* ---------- party distribution ---------- */
function drawPartyDist(){
  const k=S.dim, el=document.getElementById("partydist"); el.innerHTML="";
  const levels = ["0","1","2","3","4","not enough evidence"];
  const rows = [];
  for (const p of ["D","R","I"]){
    const xs = M.filter(m=>inCong(m) && m.party===p); if(!xs.length) continue;
    for (const m of xs){ const v=m.scores[k]; rows.push({party:`${PNAME[p]} (${xs.length})`, p, level: v==null?"not enough evidence":String(Math.round(v)), n:1/xs.length}); }
  }
  const agg = d3.rollups(rows, v=>({n:d3.sum(v,d=>d.n), c:v.length}), d=>d.party, d=>d.level).flatMap(([party,ls])=>ls.map(([level,o])=>({party,level,...o})));
  const col = [...ramp(), css("--nodata")];
  const W = widthOf(el);
  el.append(Plot.plot({width:W, height:150, marginLeft:140, marginRight:20, style:plotStyle(),
    x:{label:"share of members →", percent:true, grid:false}, y:{label:null, domain:[...new Set(agg.map(d=>d.party))].sort((a,b)=>"DRI".indexOf(a[0])-"DRI".indexOf(b[0]))},
    color:{domain:levels, range:col},
    marks:[Plot.barX(agg,{y:"party", x:"n", fill:"level", order:levels, inset:1, rx:2,
      tip:{fill:css("--card"), stroke:css("--line")}, channels:{Score:"level", Members:"c"}, title:d=>`${d.party}\n${d.level==="not enough evidence"?"Not enough evidence":LEVELS[k][+d.level]}: ${d.c} members (${Math.round(d.n*100)}%)`})]}));
  document.getElementById("pd-legend").innerHTML = legendHTML(levels.map((l,i)=>[l==="not enough evidence"?"Not enough evidence":LEVELS[k][+l], col[i]]));
}

/* ---------- which rules they support (diverging bars) ---------- */
const pct = v => v>0 && v<0.005 ? "<1%" : Math.round(v*100)+"%";
const RFGROUP = {harms:"Everyday harms", frontier:"Catastrophic and frontier risk"};
const RFKIND = [[2,"Explicit support"],[1,"Implied support"],[-1,"Implied opposition"],[-2,"Explicit opposition"]];
function rfColor(v){ const c=d3.color(css(v>0?"--r4":"--r0")); if (Math.abs(v)===1) c.opacity=0.45; return c.formatRgb(); }
// who the policy chart covers: Congress (reg_focus labels) or federal officials / institutions (federal analysis)
function rfSource(){
  if (S.who==="congress" || !FED) return {ms: M.filter(m=>inCong(m) && partyOk(m)), get: rfStance, noun:"members", fed:false};
  const inst = S.who==="institutions";
  return {ms: FED.members.filter(m=>(m.entity_type==="institution")===inst), get:(m,a)=>(m.regulation?.areas?.[a]?.stance)||0, noun: inst?"institutions":"officials", fed:true};
}
function rfStance(m, a){ const r = RF && RF.m[m.id] && RF.m[m.id][a]; return r ? r[0] : 0; }
function drawRegFocus(){
  const el = document.getElementById("rfchart"); el.innerHTML = "";
  if (!RF){ el.innerHTML = '<p class="note">No data yet.</p>'; return; }
  const src = rfSource(), ms = src.ms, N = ms.length;
  setTitle("regfocus", `Which AI policies ${src.noun} support`);
  const rows = RF.areas.map(([a,name,g,sup,opp])=>{ const c={2:0,1:0,"-1":0,"-2":0};
    for (const m of ms){ const v=src.get(m,a); if (v) c[v]++; }
    return {a, name, g, sup, opp, c, s:(c[2]+c[1])/N, o:(c[-1]+c[-2])/N}; });
  const groups = ["harms","frontier"].map(g=>({g, rows: rows.filter(r=>r.g===g).sort((x,y)=>y.s-x.s || x.o-y.o)}));
  const W = widthOf(el), narrow = W < 560, LW = narrow ? 128 : 262, RH = 26, GH = 30, PADR = 44, PADL = 40;
  const maxS = d3.max(rows, r=>r.s) || .01, maxO = d3.max(rows, r=>r.o) || .01;
  const plotW = W - LW - PADL - PADR;
  const x0 = LW + PADL + plotW * maxO / (maxS + maxO);
  const xs = d3.scaleLinear().domain([0, maxS + maxO]).range([0, plotW]);
  const H = groups.reduce((h,g)=>h + GH + g.rows.length*RH, 0) + 26;
  const svg = d3.select(el).append("svg").attr("viewBox",`0 0 ${W} ${H}`).attr("width",W).attr("height",H).attr("role","img")
    .attr("aria-label","Percent of members who support or oppose each AI policy");
  const fg = css("--fg"), mu = css("--muted");
  let y = 0; const segs = [];
  for (const G of groups){
    svg.append("text").attr("x",0).attr("y",y+GH-9).attr("fill",fg).attr("font-size",13).attr("font-weight",600).text(RFGROUP[G.g]);
    y += GH;
    for (const r of G.rows){
      const cy = y + RH/2;
      svg.append("text").attr("x",LW).attr("y",cy).attr("dy","0.35em").attr("text-anchor","end").attr("fill",fg).attr("font-size",narrow?11:12.5)
        .text(narrow && r.name.length>21 ? r.name.slice(0,20)+"…" : r.name).append("title").text(r.name);
      // explicit next to the center line, implied outside it
      let xr = x0, xl = x0;
      for (const v of [2,1]){ const w = xs(r.c[v]/N); if (w>0){ segs.push({r, v, x:xr, w, y:y+5}); xr += w; } }
      for (const v of [-2,-1]){ const w = xs(r.c[v]/N); if (w>0){ xl -= w; segs.push({r, v, x:xl, w, y:y+5}); } }
      if (r.s>0) svg.append("text").attr("x",xr+5).attr("y",cy).attr("dy","0.35em").attr("fill",mu).attr("font-size",11).text(pct(r.s));
      if (r.o>0) svg.append("text").attr("x",xl-5).attr("y",cy).attr("dy","0.35em").attr("text-anchor","end").attr("fill",mu).attr("font-size",11).text(pct(r.o));
      y += RH;
    }
  }
  svg.append("line").attr("x1",x0).attr("x2",x0).attr("y1",GH-6).attr("y2",y).attr("stroke",css("--muted")).attr("stroke-width",1);
  svg.append("text").attr("x",x0-6).attr("y",y+16).attr("text-anchor","end").attr("fill",mu).attr("font-size",11).text("← oppose");
  svg.append("text").attr("x",x0+6).attr("y",y+16).attr("fill",mu).attr("font-size",11).text("support →");
  const pc = (n)=>`${n} (${Math.round(n/N*100)}%)`;
  const party = (r, sgn)=>src.fed ? "" : ["D","R","I"].map(p=>{ const n=ms.filter(m=>m.party===p && Math.sign(rfStance(m,r.a))===sgn).length; return n?`${p} ${n}`:""; }).filter(Boolean).join(" · ");
  svg.append("g").selectAll("rect").data(segs).join("rect")
    .attr("x",d=>d.x+(d.v>0?1:0)).attr("y",d=>d.y).attr("width",d=>Math.max(1,d.w-1)).attr("height",RH-10).attr("rx",2)
    .attr("fill",d=>rfColor(d.v)).classed("hit",true)
    .on("mousemove",(e,d)=>{ const r=d.r; showTip(e, `<b>${esc(r.name)}</b><br><span class="note">Support means: ${esc(r.sup)}</span><br>`+
      `Support: <b>${pc(r.c[2]+r.c[1])}</b>: ${r.c[2]} explicit, ${r.c[1]} implied${party(r,1)?` · ${party(r,1)}`:""}<br>`+
      `Oppose: <b>${pc(r.c[-1]+r.c[-2])}</b>: ${r.c[-2]} explicit, ${r.c[-1]} implied${party(r,-1)?` · ${party(r,-1)}`:""}<br><span class="note">Out of ${N} ${src.noun}. Click to see them.</span>`); })
    .on("mouseleave",hideTip).on("click",(e,d)=>{ hideTip(); rfSel={a:d.r.a, name:d.r.name, sgn:Math.sign(d.v)}; listRF(); });
  document.getElementById("rf-legend").innerHTML = RFKIND.map(([v,l])=>`<span><i style="background:${rfColor(v)}"></i>${l}</span>`).join("");
  listRF();
}
function listRF(){
  const cap=document.getElementById("rf-cap"), box=document.getElementById("rf-names");
  if (!rfSel){ cap.textContent=""; box.innerHTML=""; return; }
  const src = rfSource();
  const list = src.ms.filter(m=>Math.sign(src.get(m,rfSel.a))===rfSel.sgn)
    .sort((a,b)=>Math.abs(src.get(b,rfSel.a))-Math.abs(src.get(a,rfSel.a)) || (b.n||b.n_statements||0)-(a.n||a.n_statements||0));
  cap.innerHTML = `<b>${esc(rfSel.name)}</b>: ${src.noun} who ${rfSel.sgn>0?"support":"oppose"} it (${list.length})`;
  const kind = m=>Math.abs(src.get(m,rfSel.a))===2?"explicit":"implied";
  if (!src.fed) { nameChips(box, list, kind); return; }
  box.innerHTML = list.map(m=>`<a class="nm" style="text-decoration:none" href="federal.html?scope=${S.who}&profile=${encodeURIComponent(m.id)}">${esc(m.name)} <span class="note">${esc(m.organization_name||"")}</span><b>${kind(m)}</b></a>`).join("");
}

/* ---------- key events, drawn as dashed lines on the time charts ---------- */
const EVENTS = [
  ["2025-12-11","State AI law order","Trump signs an executive order that seeks to preempt state AI laws."],
  ["2026-04-07","Project Glasswing","Anthropic announces Project Glasswing: its unreleased Claude Mythos model finds software vulnerabilities at scale."],
  ["2026-08-26","Hugging Face reports","OpenAI and METR/Redwood publish reports on the July incident in which AI agents escaped a test sandbox and hacked Hugging Face."],
  ["2026-09-25","US–China summit","Trump–Xi summit in Washington ends with an AI incident channel and a U.S.–China dialogue on superintelligence."],
  ["2026-11-05","METR AI R&D report","METR reports that AI has roughly doubled the pace of AI research at Anthropic."],
].map(([d,label,what])=>({d:new Date(d+"T00:00:00Z"), label, what}));
// rules plus labels in the top margin. Each label goes on the lowest row where it does not overlap another label;
// labels near the right edge face left. Returns the marks and the top margin they need.
function eventMarks(lo, hi, W, ml, mr, numbered=true){   // numbers with a key; names next to the lines were too cluttered
  if (!S.events) return {top: 20, key: "", marks: []};
  const ev = EVENTS.map((e,i)=>({...e, label: numbered ? String(i+1) : e.label, i})).filter(e=>e.d>=lo && e.d<=hi), rows = [];
  for (const e of ev){
    const px = ml + (e.d-lo)/(hi-lo||1)*(W-ml-mr), w = e.label.length*5.8+10;
    e.end = !numbered && px + w > W - 4;
    const a = numbered ? px-7 : e.end ? px-w : px, b = numbered ? px+7 : e.end ? px : px+w;
    e.row = rows.findIndex(r=>r.every(([x,y])=>b<=x || a>=y)); if (e.row<0){ e.row=rows.length; rows.push([]); }
    rows[e.row].push([a,b]);
  }
  // too crowded for names: use numbers and a key under the chart
  if (!numbered && rows.length > 3) return eventMarks(lo, hi, W, ml, mr, true);
  const mu = css("--muted"), n = Math.max(1, rows.length);
  const key = numbered ? `<p class="note evkey">${ev.map(e=>`<b>${e.i+1}</b> ${esc(EVENTS[e.i].label)} (${e.d.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"})})`).join(" · ")}</p>` : "";
  return {top: 30 + n*13, key, marks: [Plot.ruleX(ev,{x:"d", stroke:mu, strokeOpacity:.6, strokeDasharray:"3 3"}),
    // Plot needs constant dx/dy, so one text mark per row and side
    ...d3.range(n).flatMap(r=>[false,true].map(end=>Plot.text(ev.filter(e=>e.row===r && e.end===end),{x:"d", frameAnchor:"top", text:"label",
      fill:mu, fontSize:10.5, dy:-16-(n-1-r)*13,   // well above the frame, clear of the top gridline and the data
      dx:numbered?0:end?-4:4, textAnchor:numbered?"middle":end?"end":"start", fontWeight:numbered?600:400, title:e=>`${e.d.toISOString().slice(0,10)}: ${e.what}`})))]};
}

/* ---------- topics ---------- */
function quarters(){ return [...new Set(TL.map(r=>r.q))].sort(); }
// the topic charts follow the question picked in the top bar
const TOPIC_OF = {ai_overall:"jobs/economy", agi_pilled:"AGI/transformative", x_risk:"x-risk/loss of control", china_race:"China/competition", regulation:"regulation"};
const TOPIC_NAME = {"jobs/economy":"jobs and the economy", "AGI/transformative":"AGI and transformative AI", "x-risk/loss of control":"x-risk and loss of control", "China/competition":"China and competition", "regulation":"AI rules"};
function drawFocus(){
  const t=TOPIC_OF[S.dim], el=document.getElementById("focuschart"); el.innerHTML="";
  setTitle("topicshare", `Share of AI statements about ${TOPIC_NAME[t]}, by party`);
  if (!DAILY){ el.innerHTML='<p class="note">No daily data yet.</p>'; return; }
  const ti = DAILY.topics.indexOf(t), gs = GROUPS_IN(S.cong), WIN = 30;
  const end = new Date(UPDATED+"T00:00:00Z"), day = 864e5;
  const start = S.range==="all" ? new Date("2023-02-01T00:00:00Z") : new Date(end - (+S.range)*day);
  const key = d => d.toISOString().slice(0,10);
  const data = [];
  for (const p of ["D","R"]){
    const tot = new Map(), on = new Map();
    for (const [d,pa,g,k,n] of DAILY.rows){ if (pa!==p || !gs.has(g)) continue; tot.set(d,(tot.get(d)||0)+n); if (k===ti) on.set(d,(on.get(d)||0)+n); }
    let a=0, b=0; const q=[];
    for (let d=new Date(start - WIN*day); d<=end; d=new Date(+d+day)){
      const k=key(d); a+=tot.get(k)||0; b+=on.get(k)||0; q.push([tot.get(k)||0, on.get(k)||0]);
      if (q.length>WIN){ const [x,y]=q.shift(); a-=x; b-=y; }
      if (d>=start && a>=10) data.push({d:new Date(+d), p, party:PNAME[p], share:b/a, n:Math.round(b), tot:Math.round(a)});
    }
  }
  const W=widthOf(el);
  // end labels: push apart when the two lines end close together
  const ends = data.filter((d,i,a)=>!a[i+1] || a[i+1].p!==d.p).map(d=>({...d}));
  if (ends.length===2){ const [hi,lo] = ends[0].share>=ends[1].share ? ends : [ends[1],ends[0]]; hi.dy=-7; lo.dy=7; }
  const lo = d3.min(data,d=>d.d), hi = d3.max(data,d=>d.d), EV = eventMarks(lo, hi, W, 48, 96);
  el.append(Plot.plot({width:W, height:290, marginLeft:48, marginRight:96, marginTop:EV.top, style:plotStyle(),
    x:{type:"utc", label:null, domain:[lo,hi]}, y:{label:null, percent:true, grid:true, tickFormat:d=>d+"%"},
    color:{domain:["Democrats","Republicans"], range:[PC("D"),PC("R")]},
    marks:[Plot.ruleY([0],{stroke:css("--line")}),
      ...EV.marks,
      Plot.line(data,{x:"d", y:"share", z:"party", stroke:"party", strokeWidth:2}),
      ...[-7,7,0].map(dy=>Plot.text(ends.filter(d=>(d.dy||0)===dy),{x:"d", y:"share", text:"party", fill:"party", dx:6, dy, textAnchor:"start", fontWeight:600})),
      Plot.tip(data, Plot.pointerX({x:"d", y:"share", z:"party", fill:css("--card"), stroke:css("--line"), channels:{Date:d=>d.d.toISOString().slice(0,10), Party:"party", Share:d=>`${(d.share*100).toFixed(1)}%`, Statements:d=>`${d.n} of ${d.tot} in 30 days`}, format:{x:false, y:false, fill:false, stroke:false, z:false}}))]}));
  el.insertAdjacentHTML("beforeend", EV.key);
}
/* ---------- members at 3+ over time ---------- */
function drawTrend(){
  const el=document.getElementById("trend"); el.innerHTML=""; const k=S.dim, d=DIMS.find(x=>x[0]===k);
  setTitle("trend-title", `Members who ${d[3]}, over time`);
  if (!HISTORY){ el.innerHTML='<p class="note">No history yet.</p>'; return; }
  const name = {all:"All members", D:"Democrats", R:"Republicans"};
  const data = HISTORY.filter(r=>r.c===S.cong && r.k===k).map(r=>({d:new Date(r.d+"T00:00:00Z"), p:r.p, who:name[r.p], v:r.hi/r.n, hi:r.hi, n:r.n})).sort((a,b)=>a.p.localeCompare(b.p) || a.d-b.d);
  const W=widthOf(el);
  const lo = d3.min(data,d=>d.d), hi = d3.max(data,d=>d.d), EV = eventMarks(lo, hi, W, 48, 110);
  el.append(Plot.plot({width:W, height:290, marginLeft:48, marginRight:110, marginTop:EV.top, style:plotStyle(),
    x:{type:"utc", label:null, domain:[lo,hi]}, y:{label:null, percent:true, grid:true, tickFormat:d=>d+"%"},
    color:{domain:["All members","Democrats","Republicans"], range:[css("--muted"), PC("D"), PC("R")]},
    marks:[Plot.ruleY([0],{stroke:css("--line")}),
      ...EV.marks,
      Plot.line(data,{x:"d", y:"v", z:"who", stroke:"who", strokeWidth:d=>d.p==="all"?1.5:2, strokeDasharray:d=>d.p==="all"?"4 3":null}),
      Plot.text(data.filter((x,i,a)=>!a[i+1] || a[i+1].p!==x.p),{x:"d", y:"v", text:"who", fill:"who", dx:6, textAnchor:"start", fontWeight:600}),
      Plot.tip(data, Plot.pointerX({x:"d", y:"v", z:"who", fill:css("--card"), stroke:css("--line"), channels:{Date:x=>x.d.toISOString().slice(0,10), Group:"who", Share:x=>`${(x.v*100).toFixed(0)}%`, Members:x=>`${x.hi} of ${x.n}`}, format:{x:false, y:false, stroke:false, z:false}}))]}));
  el.insertAdjacentHTML("beforeend", EV.key);
}
/* ---------- recent big changes ---------- */
function drawChanges(){
  const box=document.getElementById("changelist");
  const xs = (CHANGES||[]).filter(c=>(S.party==="all"||c.party===S.party) && c.old!=null && c.new!=null && Math.abs(c.new-c.old)>1);
  if (!xs.length){ box.innerHTML = `<p class="note">No score has moved by more than 1 point in the last 60 days.</p>`; return; }
  const f = v => v==null ? "–" : fmt(v);
  box.innerHTML = `<table class="changes"><thead><tr><th>Date</th><th>Member</th><th>Question</th><th>Change</th><th>Now</th><th>Cause</th></tr></thead><tbody>${
    xs.slice(0,25).map(c=>`<tr class="row" data-id="${esc(c.id)}"><td>${esc(c.date)}</td><td><span class="p${esc(c.party)}">●</span> ${esc(c.name)} <span class="note">${esc(c.party)}-${esc(c.state)}</span></td><td>${esc(dimLabel(c.dim))}</td>`+
      `<td class="chg"><span class="sc" style="${shade(c.old)}" title="${esc(levelText(c.dim,c.old))}">${f(c.old)}</span><span class="arr">→</span><span class="sc" style="${shade(c.new)}" title="${esc(levelText(c.dim,c.new))}">${f(c.new)}</span></td>`+
      `<td>${esc(levelText(c.dim,c.new))}</td><td class="note">${esc(c.cause)}</td></tr>`).join("")}</tbody></table>`;
  box.querySelectorAll("tr.row").forEach(tr=>tr.onclick=()=>openRow(tr.dataset.id, tr));   // open the member right under the row, no scrolling
}
function drawVoices(){
  const t=S.dim==="ai_overall" ? "__all" : TOPIC_OF[S.dim], el=document.getElementById("voices"); el.innerHTML="";
  setTitle("voices-title", t==="__all" ? "Members with the most AI statements" : `Members who talk most about ${TOPIC_NAME[t]}`);
  const xs = M.filter(m=>inCong(m) && partyOk(m)).map(m=>({m, v: t==="__all" ? m.n : (m.topics?.[t]||0)})).filter(d=>d.v>0).sort((a,b)=>b.v-a.v).slice(0,15);
  if (!xs.length){ el.innerHTML='<p class="note">Nobody in this selection has statements on this topic.</p>'; return; }
  const data = xs.map(d=>({name:`${d.m.name} (${d.m.party}-${seat(d.m)})`, v:Math.round(d.v), m:d.m}));
  const W=widthOf(el);
  const svg = Plot.plot({width:W, height:28*data.length+40, marginLeft:230, marginRight:40, style:plotStyle(),
    x:{label:"statements →", grid:true}, y:{label:null, domain:data.map(d=>d.name)},
    marks:[Plot.barX(data,{y:"name", x:"v", fill:d=>PC(d.m.party), insetTop:4, insetBottom:4, rx:3}),
      Plot.text(data,{y:"name", x:"v", text:"v", dx:6, textAnchor:"start", fill:css("--muted")})]});
  el.append(svg);
  bindHover(svg.querySelectorAll("g[aria-label=bar] rect"), data, d=>memberTip(d.m), d=>goMember(d.m));
}

/* ---------- opportunity map ---------- */
const PRESETS = [
  {label:"Expect AGI, low x-risk", rule:"AGI score of 3 or more, and x-risk score of 1.5 or less (or no score)", f:m=>(m.scores.agi_pilled??-1)>=3 && (m.scores.x_risk==null || m.scores.x_risk<=1.5)},
  {label:"High x-risk, low regulation", rule:"x-risk score of 3 or more, and regulation score of 2 or less (or no score)", f:m=>(m.scores.x_risk??-1)>=3 && (m.scores.regulation==null || m.scores.regulation<=2)},
  {label:"High China race, high x-risk", rule:"China race score of 3 or more, and x-risk score of 3 or more", f:m=>(m.scores.china_race??-1)>=3 && (m.scores.x_risk??-1)>=3},
  {label:"High regulation, low x-risk", rule:"regulation score of 3 or more, and x-risk score of 1 or less (or no score)", f:m=>(m.scores.regulation??-1)>=3 && (m.scores.x_risk==null || m.scores.x_risk<=1)},
  {label:"High AI overall, high regulation", rule:"AI overall score of 3 or more, and regulation score of 3 or more", f:m=>(m.scores.ai_overall??-1)>=3 && (m.scores.regulation??-1)>=3},
];
function drawPresets(){
  document.getElementById("presets").innerHTML = PRESETS.map((p,i)=>`<button data-preset="${i}" aria-pressed="${i===S.preset}">${esc(p.label)}</button>`).join("");
  document.querySelectorAll("[data-preset]").forEach(b=>b.onclick=()=>{S.preset=+b.dataset.preset; drawList();});
}
function drawList(){
  if (S.preset==null) S.preset = 2;
  document.querySelectorAll("[data-preset]").forEach(b=>b.setAttribute("aria-pressed", S.preset===+b.dataset.preset));
  const list = M.filter(m=>inCong(m) && partyOk(m)).filter(PRESETS[S.preset].f).sort((a,b)=>b.n-a.n);
  const byP = d3.rollup(list, v=>v.length, m=>m.party);
  document.getElementById("list-cap").innerHTML = `Rule: ${PRESETS[S.preset].rule}. <b>${list.length}</b> members${list.length?` (${["D","R","I"].filter(p=>byP.get(p)).map(p=>`${PNAME[p]} ${byP.get(p)}`).join(", ")})`:""}. Members with the most statements are first.`;
  nameChips(document.getElementById("list-names"), list);
}
function nameChips(box, list, extra){
  box.innerHTML = list.slice(0,80).map(m=>`<span class="nm" data-id="${m.id}"><span class="p${m.party}">●</span> ${esc(m.name)} <span class="note">${m.party}-${seat(m)}</span>${extra?`<b>${extra(m)}</b>`:""}</span>`).join("") + (list.length>80?`<span class="note">…and ${list.length-80} more</span>`:"");
  box.querySelectorAll(".nm").forEach(n=>{ const m=M.find(x=>x.id===n.dataset.id); n.onmousemove=e=>showTip(e,memberTip(m)); n.onmouseleave=hideTip; n.onclick=()=>{hideTip();goMember(m);}; });
}

/* ---------- committees ---------- */
let commSel = null;
function drawComm(){
  const k=S.dim, el=document.getElementById("comm"); el.innerHTML="";
  const rows = [];
  for (const [c,label] of Object.entries(COMM)){
    const ms = M.filter(m=>m.status==="current" && partyOk(m) && m.committees.some(x=>x.c===c));
    for (const [st] of STATES) { const lab = stateLabel(st); const n = ms.filter(m=>stateOf(m)===st).length; rows.push({c, label, st, lab, n, tot:ms.length, share:n/(ms.length||1)}); }
  }
  const order = Object.keys(COMM).sort((a,b)=>{ const f=c=>rows.find(r=>r.c===c&&r.st==="yes").share; return f(b)-f(a); }).map(c=>COMM[c]);
  const W=widthOf(el);
  const svg = Plot.plot({width:W, height:order.length*30+40, marginLeft:190, marginRight:70, style:plotStyle(),
    x:{label:"share of committee members →", percent:true, grid:true, tickFormat:d=>d+"%"}, y:{label:null, domain:order},
    color:{domain:STATES.map(s=>s[0]), range:STATES.map(s=>css(s[2]))},
    marks:[Plot.barX(rows.filter(r=>r.n>0),{y:"label", x:"share", fill:"st", order:STATES.map(s=>s[0]), stroke:d=>d.st==="none"?css("--muted"):css("--card"), strokeWidth:d=>d.st==="none"?1:1.5, insetTop:5, insetBottom:5}),
      Plot.text(rows.filter(r=>r.st==="yes"),{y:"label", x:1, text:d=>`${d.n} of ${d.tot}`, dx:8, textAnchor:"start", fill:css("--muted")})]});
  el.append(svg);
  bindHover(svg.querySelectorAll("g[aria-label=bar] rect"), rows.filter(r=>r.n>0), d=>`<b>${esc(d.label)}</b><br>${esc(d.lab)}: ${d.n} of ${d.tot} members`, d=>{commSel=d; listComm();});
  document.getElementById("comm-legend").innerHTML = stateLegend();
  listComm();
}
function listComm(){
  const cap=document.getElementById("comm-cap"), box=document.getElementById("comm-names");
  if (!commSel){ cap.textContent="Click a bar to see the members."; box.innerHTML=""; return; }
  const k=S.dim, list = M.filter(m=>m.status==="current" && partyOk(m) && m.committees.some(x=>x.c===commSel.c) && stateOf(m)===commSel.st).sort((a,b)=>(b.scores[k]??0)-(a.scores[k]??0) || b.n-a.n);
  cap.innerHTML = `<b>${esc(commSel.label)}</b>: ${esc(commSel.lab)} (${list.length})`;
  nameChips(box, list, m=>{ const r=m.committees.find(x=>x.c===commSel.c); return (r.title?esc(r.title)+" · ":"")+fmt(m.scores[k]); });
}

/* ---------- table ---------- */
function renderHead(){
  const cols = [["name","Name"],["seat","Party–seat"],["chamber","Chamber"],...DIMS.map(([k,l])=>[k,l]),["strength","Evidence"],["n","Quotes"]];
  document.querySelector("#tbl thead").innerHTML = "<tr>"+cols.map(([k,l])=>`<th data-k="${k}" class="${DIMS.some(d=>d[0]===k)||k==="n"?"num":""}">${l}${sortKey===k?(sortDir>0?" ▲":" ▼"):""}</th>`).join("")+"</tr>";
  document.querySelectorAll("#tbl th").forEach(th=>th.onclick=()=>{const k=th.dataset.k; sortDir = sortKey===k ? -sortDir : (k==="name"||k==="seat"?1:-1); sortKey=k; renderHead(); renderTable();});
}
const SORTV = {name:m=>m.name, seat:m=>m.state+String(m.district??"").padStart(2,"0"), chamber:m=>m.chamber, strength:m=>({high:3,medium:2,low:1}[m.strength]||0), n:m=>m.n};
function shade(v){ if(v==null) return ""; const c=d3.color(scoreColor(v)); c.opacity=0.55; return `background:${c.formatRgb()}`; }
function renderTable(){
  const q = document.getElementById("q").value.toLowerCase().trim(), ch=fch.value, pa=fpa.value, st=fst.value, evf=fev.value;
  const stOk = m => !st || (st==="c119"?inCong(m,"119"): st==="c120"?inCong(m,"120"): m.next===st);
  let rows = M.filter(m=>(!q || m.name.toLowerCase().includes(q) || m.state.toLowerCase()===q || seat(m).toLowerCase()===q)
    && (!ch||m.chamber===ch) && (!pa||m.party===pa) && stOk(m) && (!evf||m.n>0));
  const f = SORTV[sortKey] || (m=>m.scores[sortKey] ?? (sortDir>0?99:-99));
  rows.sort((a,b)=>{const x=f(a),y=f(b);return (x>y?1:x<y?-1:0)*sortDir || a.name.localeCompare(b.name);});
  const tb = document.querySelector("#tbl tbody");
  tb.innerHTML = rows.map(m=>`<tr class="row" data-id="${m.id}"><td>${esc(m.name)}${m.status==="member_elect"?'<span class="badge">new member</span>':""}${m.next==="departing"?'<span class="badge">leaving</span>':""}${m.reviewed?'<span class="badge" title="Checked by a person">human-reviewed</span>':""}</td>
    <td class="p${m.party}">${m.party}-${seat(m)}</td><td>${m.chamber==="senate"?"Senate":"House"}${m.next_chamber!==m.chamber?` → ${m.next_chamber==="senate"?"Senate":"House"}`:""}</td>
    ${DIMS.map(([k])=>`<td class="num"><span class="sc" style="${shade(m.scores[k])}">${fmt(m.scores[k])}</span></td>`).join("")}
    <td>${m.strength==="none"?"—":m.strength}</td><td class="num">${m.n}</td></tr>`).join("");
  tb.querySelectorAll("tr.row").forEach(tr=>tr.onclick=()=>openRow(tr.dataset.id));
  if (open && !document.querySelector("#changelist tr.detail")) { const id = open; open = null; openRow(id); }
}
async function openRow(id, tr){   // tr: the row to open under (default: the member's row in the members table)
  tr = tr || document.querySelector(`#tbl tr.row[data-id="${id}"]`); if(!tr) return;
  const same = open===id && tr.nextElementSibling?.classList.contains("detail");
  document.querySelectorAll("tr.detail").forEach(x=>x.remove());
  if (same){ open=null; return; }
  open = id;
  const m = M.find(x=>x.id===id);
  const det = document.createElement("tr"); det.className="detail";
  const span = tr.children.length;
  det.innerHTML = `<td colspan="${span}">Loading…</td>`; tr.after(det);
  const d = await fetch(`data/quotes/${id}.json`).then(r=>r.json());
  QUOTES[id] = d.quotes;
  const cited = new Set(Object.values(d.cited).flat());
  const qs = [...d.quotes].sort((a,b)=>(cited.has(b.sid)-cited.has(a.sid)) || String(b.date).localeCompare(String(a.date)));
  const srcName = {floor:"Floor speech",hearing:"Hearing",x:"X post",web:"Web",official:"Official"};
  const comms = (m.committees||[]).map(c=>COMM[c.c]+(c.title?` (${c.title})`:"")).join(" · ");
  det.innerHTML = `<td colspan="${span}">
    <p style="margin:0 0 8px"><button type="button" class="citebtn" style="margin:0" data-cite="member-${esc(id)}">${QICON}Cite ${esc(m.name)}'s scores</button></p>
    <p style="margin:0 0 6px">${esc(m.summary || "Not enough public statements about AI to summarize.")}</p>
    ${m.handle?`<p class="note" style="margin:0">X: <a href="https://x.com/${esc(m.handle)}" target="_blank" rel="noopener">@${esc(m.handle)}</a></p>`:""}
    ${comms?`<p class="note" style="margin:0">Committees: ${esc(comms)}</p>`:""}
    ${rfLine(id)}
    <div class="dims">${DIMS.map(([k,l])=>`<div class="dim"><b>${l}: ${fmt(m.scores[k])}</b>${esc(clean(m.just[k])||"Insufficient evidence.")}</div>`).join("")}</div>
    <p class="note">${qs.length} verified statement${qs.length===1?"":"s"}. Statements that the scores use have a color mark and are first. Each box tag shows the level that each model gave the statement on one question (Claude / GPT). A dash means that the model did not give a level.</p>
    ${qs.slice(0,60).map(q=>`<div class="quote ${cited.has(q.sid)?"cited":""}">“${esc(q.text)}”<div class="src">${srcName[q.src]||q.src} · ${esc(q.date||"undated")} · <a href="${esc(q.url)}" target="_blank" rel="noopener">source</a> <button type="button" class="citebtn" data-quote="${esc(id)}|${esc(q.sid)}">Copy quote</button> ${q.topics.map(t=>`<span class="chip">${esc(t)}</span>`).join("")} ${labChips(q)}</div></div>`).join("")}
    ${qs.length>60?`<p class="note">…and ${qs.length-60} more in the CSV and the GitHub data.</p>`:""}</td>`;
}
addEventListener("themechange", ()=>{ drawAll(); if (document.getElementById("tbl")) renderTable(); });
function rfLine(id){
  const r = RF && RF.m[id]; if (!r) return "";
  const nm = a => (RF.areas.find(x=>x[0]===a)||[a,a])[1];
  const part = sgn => Object.entries(r).filter(([a,v])=>Math.sign(v[0])===sgn)
    .map(([a,v])=>`<span class="chip" title="${esc((Math.abs(v[0])===2?"Explicit. ":"Implied. ")+v[2]+" ("+v[1].join(", ")+")")}">${esc(nm(a))}</span>`).join("");
  const s = part(1), o = part(-1);
  if (!s && !o) return "";
  return `<p class="note" style="margin:4px 0 0">${s?`Policies they support: ${s}`:""}${s&&o?"<br>":""}${o?`Policies they oppose: ${o}`:""}</p>`;
}
function quoteText(pid, sid){
  const m = M.find(x=>x.id===pid), q = (QUOTES[pid]||[]).find(x=>x.sid===sid); if (!m || !q) return null;
  return `"${q.text.replace(/\s+/g," ").trim()}" (${m.name}, ${m.party}-${seat(m)}, ${q.date||"undated"}). Source: ${q.url}. Via ${SITE}, ${pageURL("member-"+pid)}`;
}
function addCiteButtons(){
  for (const id of ["chamber","ideo-title","party","trend-title","changes","regfocus","policy-title","topics","topicshare","voices-title","lists","committees","members"]) {
    const h = document.getElementById(id); if (!h || h.querySelector(".citebtn")) continue;
    const b = document.createElement("button"); b.type="button"; b.className="citebtn"; b.dataset.cite=id; b.innerHTML = QICON + "Cite";
    b.setAttribute("aria-label", "Cite this section"); h.append(b);
  }
}
// links: #method opens the collapsed Method section; #member-ID opens that member
function openHash(){
  if (location.hash==="#method") document.getElementById("method").open = true;
  const m = location.hash.startsWith("#member-") && M.find(x=>x.id===location.hash.slice(8));
  if (m) goMember(m);
}
addEventListener("hashchange", openHash);
if (document.body.dataset.page==="congress") document.getElementById("brand").onclick = e => { e.preventDefault(); history.replaceState(null, "", location.pathname + location.search); scrollTo({top:0, behavior:"smooth"}); };
const TOCL = [...document.querySelectorAll(".toc a")];
function tocActive(){
  let cur = null;
  for (const a of TOCL){ const el = document.getElementById(a.getAttribute("href").slice(1)); if (el && el.getBoundingClientRect().top < 170) cur = a; }
  TOCL.forEach(a=>a.classList.toggle("active", a===cur));
}
addEventListener("scroll", ()=>requestAnimationFrame(tocActive), {passive:true});
init().then(()=>{ addCiteButtons(); openHash(); tocActive(); });
