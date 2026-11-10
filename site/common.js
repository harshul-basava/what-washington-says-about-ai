/* Shared by every page: theme switch (remembered across pages), cite dialog, copy and toast. */
(function(){
  const r = document.documentElement, b = document.getElementById("theme");
  const label = ()=>{ if (b) b.setAttribute("aria-label", r.dataset.theme==="dark" ? "Switch to light mode" : "Switch to dark mode"); };
  label();
  if (b) b.onclick = ()=>{ r.dataset.theme = r.dataset.theme==="dark" ? "light" : "dark";
    try { localStorage.setItem("theme", r.dataset.theme); } catch(e) {}
    label(); dispatchEvent(new Event("themechange")); };
})();
/* ---------- cite / quote ---------- */
const QICON = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M7.2 6C4.9 7.2 3.5 9.3 3.5 12v6h6.5v-6.3H6.6c.1-1.7 1-3 2.6-3.8zm10 0c-2.3 1.2-3.7 3.3-3.7 6v6H20v-6.3h-3.4c.1-1.7 1-3 2.6-3.8z"/></svg>';
const QUOTES = {};
const SITE = "What Washington Says About AI";
function pageURL(anchor){ return location.origin + location.pathname + (anchor ? "#" + anchor : ""); }
function today(){ return new Date().toISOString().slice(0,10); }
function toast(msg){ const t=document.getElementById("toast"); t.textContent=msg; t.classList.add("on"); clearTimeout(t._h); t._h=setTimeout(()=>t.classList.remove("on"),1800); }
async function copy(text, msg){ try { await navigator.clipboard.writeText(text); toast(msg||"Copied"); } catch(e) { toast("Copy failed. Select the text and copy it."); } }
function citation(anchor){
  let title = SITE, what = "the whole page";
  if (anchor && anchor.startsWith("member-")) {
    const m = typeof M!=="undefined" && M.find(x=>x.id===anchor.slice(7)); if (m) { title = `${m.name}: AI scores and statements`; what = `the scores and statements of ${m.name}`; }
  } else if (anchor) {
    const h = document.getElementById(anchor); const t = h && (h.querySelector("h2")||h).firstChild?.textContent?.trim();
    if (t) { title = t; what = `the chart "${t}"`; }
  }
  const UPD = (typeof UPDATED!=="undefined" && UPDATED) || today();
  const url = pageURL(anchor), year = UPD.slice(0,4) || new Date().getFullYear(), key = "wwsai" + year + (anchor ? anchor.replace(/[^a-z0-9]/gi,"") : "");
  const text = title===SITE ? `${SITE}. (${year}). Data updated ${UPD}. ${url} (accessed ${today()}).`
                            : `${SITE}. (${year}). "${title}." Data updated ${UPD}. ${url} (accessed ${today()}).`;
  const bib = `@misc{${key},\n  title = {${title===SITE ? SITE : title + " (" + SITE + ")"}},\n  year = {${year}},\n  note = {Data updated ${UPD}; accessed ${today()}},\n  howpublished = {\\url{${url}}}\n}`;
  return {text, bib, url, what};
}
function openCite(anchor){
  const c = citation(anchor);
  document.getElementById("citehead").textContent = !anchor ? "Cite this page" : anchor.startsWith("member-") ? "Cite this member" : "Cite this chart";
  document.getElementById("citewhat").textContent = `This cites ${c.what}.`;
  document.getElementById("cite-text").textContent = c.text;
  document.getElementById("cite-bib").textContent = c.bib;
  document.getElementById("cite-url").textContent = c.url;
  document.getElementById("citedlg").showModal();
}
// click on the dimmed area outside the box closes it
document.getElementById("citedlg").addEventListener("click", e=>{ const d=e.currentTarget, r=d.getBoundingClientRect();
  if (e.target===d && (e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom)) d.close(); });
document.addEventListener("click", e=>{
  const c = e.target.closest("[data-cite]"); if (c) { e.stopPropagation(); openCite(c.dataset.cite==="page" ? "" : c.dataset.cite); return; }
  const q = e.target.closest("[data-quote]"); if (q) { e.stopPropagation(); const [pid,sid]=q.dataset.quote.split("|"); const t=typeof quoteText==="function" && quoteText(pid,sid); if (t) copy(t,"Quote copied with its source"); return; }
  const k = e.target.closest("[data-copy]"); if (k) { copy(document.getElementById(k.dataset.copy).textContent); return; }
}, true);

// "About" and "Method" go to the method section; open it if it is a collapsed <details>
document.addEventListener("click", e=>{
  const a = e.target.closest('a[href="#method"]'); if (!a) return;
  const m = document.getElementById("method"); if (m && m.tagName==="DETAILS") m.open = true;
  if (location.hash === "#method" && m) { e.preventDefault(); m.scrollIntoView({behavior:"smooth"}); }
  document.activeElement && document.activeElement.blur();
});
document.addEventListener("click", e=>{ if (e.target.closest(".navmenu-list [data-cite]")) document.activeElement && document.activeElement.blur(); }, true);
