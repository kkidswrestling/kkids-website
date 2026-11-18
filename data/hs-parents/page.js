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
  const CK = "kk-family-checks-2627", QK = "kk-family-quiz-2627-v2";

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
    setCheck("c2", true);
    const t = $("#check"); sheet.scrollTo({top: t.offsetTop - 70, behavior: "instant"});
  });
  syncSheet();

  // ---------- Quick check ----------
  const Q = [
    {q: "Your son is too ill to attend school. What has to happen?",
     o: ["Nothing. Missing school covers it.", "You email the athletic office.", "He texts Coach Provini before 2:00 p.m."], a: 2,
     why: "A quick text before 2:00 lets the coaches know he’s taken care of and plan practice without him."},
    {q: "Your son needs a dentist appointment. When is the best time to book it?",
     o: ["During practice. Appointments count as excused.", "Outside of practice when you can, so he doesn’t miss training.", "Whenever is easiest. Practice is flexible."], a: 1,
     why: "We know family schedules are busy. You have the practice schedule, so please book around it when you can. Appointments during practice aren’t excused, but emergencies are always handled case by case."},
    {q: "He isn’t on weight when the bus leaves for an away competition. What happens?",
     o: ["He weighs in again when the team gets there.", "He sits out that day’s competition.", "He moves up a weight class."], a: 1,
     why: "Weight has to be made before the bus leaves. It’s a tough lesson when it happens, so the coaches help every wrestler plan ahead, and healthy habits at home make a big difference."},
    {q: "He gets hurt at practice. Who should be told?",
     o: ["Nobody, unless it still hurts tomorrow.", "The coaches and the athletic trainer, right away.", "Just his teammates."], a: 1,
     why: "Tell us right away so he gets the right care. Our athletic trainers work with the best sports doctors and can get appointments quickly."},
    {q: "After an away dual meet, can he ride home with you instead of the bus?",
     o: ["Yes, if you tell a coach that night.", "Yes, if you sign a release form.", "He rides the bus, unless it’s an emergency or arranged ahead of time."], a: 2,
     why: "The team travels to and from dual meets together. If something comes up, talk to Coach Provini ahead of time. The release form is only for individual tournaments."},
    {q: "It’s July, and he’s invited to a party where alcohol is being given to minors. Can he go?",
     o: ["Yes. The honor code only applies during the season.", "Yes, as long as he doesn’t drink.", "No. The honor code applies all year."], a: 2,
     why: "We want our wrestlers safe all year, not just in season. Athletes may not attend events where drugs or alcohol are being given to minors."}
  ];
  const done = new Set(store.get(QK) || []);
  const quiz = $("#quiz");
  Q.forEach((item, i) => {
    const wrap = document.createElement("div");
    wrap.className = "q";
    wrap.innerHTML = '<p class="p"><small>Question ' + (i + 1) + ' of ' + Q.length + '</small></p><div class="opts"></div><p class="fb" role="status" hidden></p>';
    wrap.querySelector(".p").append(item.q);
    const opts = wrap.querySelector(".opts"), fb = wrap.querySelector(".fb");
    item.o.forEach((text, j) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "opt"; b.textContent = text;
      b.addEventListener("click", () => {
        if (j === item.a) {
          b.classList.add("right"); wrap.classList.add("done");
          fb.hidden = false; fb.className = "fb ok"; fb.textContent = "Right. " + item.why;
          done.add(i); store.set(QK, [...done]); update();
        } else {
          b.classList.add("wrong");
          fb.hidden = false; fb.className = "fb no"; fb.textContent = "Not quite. Try another answer.";
        }
      });
      opts.append(b);
    });
    if (done.has(i)) {
      opts.children[item.a].classList.add("right"); wrap.classList.add("done");
      fb.hidden = false; fb.className = "fb ok"; fb.textContent = "Right. " + item.why;
    }
    quiz.append(wrap);
  });
  function update() {
    $("#qcount").textContent = done.size + " of " + Q.length;
    const all = done.size === Q.length;
    $("#qdone").hidden = !all;
    const vol = $("#c6").checked;
    $("#volDone").checked = vol;
    const sb = $("#signBtn");
    const ready = all && vol;
    sb.setAttribute("aria-disabled", ready ? "false" : "true");
    sb.textContent = !all ? "Finish the quick check first" : !vol ? "Volunteer or donate first" : "Open the sign-off form";
    $("#submittedBtn").hidden = !(ready && (opened || $("#c4").checked));
    if (all) {
      const c3 = $("#c3");
      if (!c3.checked) { c3.checked = true; const s = store.get(CK) || {}; s.c3 = true; store.set(CK, s); paint(); }
    }
  }
  let opened = false;
  $("#signBtn").addEventListener("click", () => { opened = true; setTimeout(update, 300); });
  $("#submittedBtn").addEventListener("click", () => {
    setCheck("c4", true); update();
    sheet.scrollTo({top: 0, behavior: "instant"});
  });
  $("#c4").addEventListener("change", update);
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
