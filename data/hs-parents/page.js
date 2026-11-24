(() => {
  const set = () => { const h = document.querySelector(".site-head"); if (h) document.documentElement.style.setProperty("--hsp-top", h.offsetHeight + "px"); };
  set(); addEventListener("resize", set);
})();

(() => {
  "use strict";
  const $ = s => document.querySelector(s);
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  const CK = "kk-family-checks-2627";

  // ---------- Checklist ----------
  const boxes = [...document.querySelectorAll("#checks input")];
  const saved = store.get(CK) || {};
  function paint() {
    let n = 0;
    boxes.forEach(b => { b.closest("li").classList.toggle("done", b.checked); if (b.checked) n++; });
    $("#ptext").textContent = n + " of " + boxes.length + " done";
    $("#pbar").style.width = (n / boxes.length * 100) + "%";
    // Main-page sign-off card
    const signed = $("#c4").checked;
    $("#soText").textContent = n + " of " + boxes.length + " steps";
    $("#soBar").style.width = (n / boxes.length * 100) + "%";
    $("#soBtn").textContent = n ? "Continue" : "Start";
    $("#soCard").hidden = signed;
    $("#soSmall").hidden = !signed;
    $("#soDone").hidden = !signed;
  }
  boxes.forEach(b => {
    b.checked = !!saved[b.id];
    b.addEventListener("change", () => { const s = store.get(CK) || {}; s[b.id] = b.checked; store.set(CK, s); paint(); });
  });
  $("#clearChecks").addEventListener("click", () => { boxes.forEach(b => b.checked = false); store.set(CK, {}); paint(); });
  paint();

  // ---------- Topic views ----------
  try { history.scrollRestoration = "manual"; } catch (e) {}
  const topics = [...document.querySelectorAll("section.topic")].map(t => t.id);
  let homeY = 0;
  function route() {
    const id = location.hash.slice(1);
    const showing = topics.includes(id);
    if (showing && !document.body.classList.contains("viewing")) homeY = window.scrollY;
    document.body.classList.toggle("viewing", showing);
    document.querySelectorAll("section.topic").forEach(t => t.classList.toggle("active", t.id === id));
    $("#viewbar").hidden = !showing;
    if (showing) { $("#viewTitle").textContent = document.getElementById(id).dataset.title; window.scrollTo({top: 0, behavior: "instant"}); }
    else if (id === "") { window.scrollTo({top: homeY, behavior: "instant"}); }
  }
  window.addEventListener("hashchange", route);
  $("#backBtn").addEventListener("click", e => {
    e.preventDefault();
    history.replaceState(null, "", location.pathname + location.search);
    route();
  });
  route();

  // ---------- Sign-off sheet ----------
  const sheet = $("#signoff");
  function syncSheet() {
    const open = location.hash === "#signoff";
    sheet.hidden = !open;
    document.body.classList.toggle("sheet-open", open);
  }
  function closeSheet(e) {
    if (e) e.preventDefault();
    history.replaceState(null, "", location.pathname + location.search);
    syncSheet();
  }
  window.addEventListener("hashchange", syncSheet);
  $("#soClose").addEventListener("click", closeSheet);
  $("#soBack").addEventListener("click", closeSheet);
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !sheet.hidden) closeSheet(); });
  sheet.addEventListener("click", e => {
    const a = e.target.closest("a[data-go]");
    if (!a) return;
    e.preventDefault();
    const t = document.getElementById(a.dataset.go);
    if (t) sheet.scrollTo({top: t.offsetTop - 70, behavior: "instant"});
  });
  function setCheck(id, v) {
    const b = $("#" + id); if (b.checked === v) return;
    b.checked = v; const s = store.get(CK) || {}; s[id] = v; store.set(CK, s); paint();
  }
  $("#readBtn").addEventListener("click", () => {
    setCheck("c2", true); update();
    const t = $("#volstep"); sheet.scrollTo({top: t.offsetTop - 70, behavior: "instant"});
  });
  syncSheet();

  function update() {
    const all = $("#c2").checked;
    const vol = $("#c6").checked;
    $("#volDone").checked = vol;
    const sb = $("#signBtn");
    const ready = all && vol;
    sb.setAttribute("aria-disabled", ready ? "false" : "true");
    sb.textContent = !all ? "Read the key rules first" : !vol ? "Volunteer or donate first" : "Open the sign-off form";
    $("#submittedBtn").hidden = !(ready && (opened || $("#c4").checked));
  }
  let opened = false;
  $("#signBtn").addEventListener("click", () => { opened = true; setTimeout(update, 300); });
  $("#submittedBtn").addEventListener("click", () => {
    setCheck("c4", true); update();
    sheet.scrollTo({top: 0, behavior: "instant"});
  });
  $("#c4").addEventListener("change", update);
  $("#c2").addEventListener("change", update);
  $("#volDone").addEventListener("change", e => {
    const c6 = $("#c6"); c6.checked = e.target.checked;
    const s = store.get(CK) || {}; s.c6 = c6.checked; store.set(CK, s); paint(); update();
  });
  $("#c6").addEventListener("change", update);
  $("#clearChecks").addEventListener("click", update);
  update();
})();
  (() => {
    const strip = document.getElementById("dates");
    if (!strip) return;
    const t = new Date(); const today = t.getFullYear() + "-" + String(t.getMonth()+1).padStart(2,"0") + "-" + String(t.getDate()).padStart(2,"0");
    strip.querySelectorAll(".date").forEach(c => c.classList.toggle("past", c.dataset.end < today));
    const next = [...strip.querySelectorAll(".date")].find(c => c.dataset.end >= today);
    if (next && next !== strip.firstElementChild) strip.scrollLeft = next.offsetLeft - strip.firstElementChild.offsetLeft;
  })();
