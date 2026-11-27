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
    // The sign-off box came off the home screen Nov. 27 (Joe). The sign-off itself still opens at #signoff.
    const signed = $("#c4").checked;
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
  // Each step ends with its own box, kept in step with the checklist at the top.
  [["readDone", "c2"], ["volDone", "c6"], ["signDone", "c4"]].forEach(([box, ck]) => {
    $("#" + box).addEventListener("change", e => { setCheck(ck, e.target.checked); update(); });
  });
  syncSheet();

  function update() {
    const read = $("#c2").checked, vol = $("#c6").checked, signed = $("#c4").checked;
    [["readDone", "readBox", read], ["volDone", "volBox", vol], ["signDone", "signBox", signed]].forEach(([box, wrap, on]) => {
      $("#" + box).checked = on;
      $("#" + wrap).classList.toggle("done", on);
    });
    $("#readBox small").textContent = read ? "✓ Step 1 done" : "Check this box to finish step 1.";
    $("#volBox small").textContent = vol ? "✓ Step 2 done" : "Check this box to finish step 2.";
    $("#signBox small").textContent = signed ? "✓ Step 3 done. Thank you!" : "Check this box after you tap Submit on the form.";
    const ready = read && vol;
    const sb = $("#signBtn");
    sb.setAttribute("aria-disabled", ready ? "false" : "true");
    sb.textContent = ready ? "Open the sign-off form" : !read && !vol ? "Finish steps 1 and 2 first" : !read ? "Finish step 1 first" : "Finish step 2 first";
    $("#signNote").textContent = ready ? "The form opens in a new tab. Come back to this page when you’re done."
      : "This button unlocks when the boxes at the end of steps 1 and 2 are checked.";
    $("#signBox").hidden = !(ready || signed);
  }
  ["c2", "c6", "c4"].forEach(id => $("#" + id).addEventListener("change", update));
  $("#clearChecks").addEventListener("click", update);
  update();
})();
  (() => {
    const strip = document.getElementById("dates");
    if (!strip) return;
    const t = new Date(); const today = t.getFullYear() + "-" + String(t.getMonth()+1).padStart(2,"0") + "-" + String(t.getDate()).padStart(2,"0");
    strip.querySelectorAll(".date").forEach(c => c.classList.toggle("past", c.dataset.end < today));
  })();
