/* Youth Coaches' Playbook (youth/coaches/).
   Group switch, practice builder, drill library filters, coaching challenge,
   weekly check-in, and the section bar. Without JS every group shows and the
   interactive tools stay hidden; their plain versions still show. */
(function () {
  var dataEl = document.getElementById("yc-data");
  if (!dataEl) return;
  var DATA = JSON.parse(dataEl.textContent);
  var $ = function (id) { return document.getElementById(id); };
  var el = function (tag, text, cls) { var n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  var copy = function (text, btn, label) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(function () {
      btn.textContent = "Copied"; setTimeout(function () { btn.textContent = label; }, 1600);
    }, function () {});
  };
  var levels = Object.keys(DATA.levels);
  var skillsFor = function (lid) { return DATA.skills.filter(function (s) { return s.level === lid; }); };
  var byId = function (id) { return DATA.skills.filter(function (s) { return s.id === id; })[0]; };

  // ---------------------------------------------------------- group switch
  var lvlSel = $("ycp-level");
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-level-panel]"));
  var onLevel = [];
  var current = null;
  var setGroup = function (lid) {
    if (levels.indexOf(lid) < 0) lid = levels[0];
    current = lid;
    lvlSel.value = lid;
    panels.forEach(function (p) { p.hidden = p.dataset.levelPanel !== lid; });
    store.set("yc-level", lid);
    onLevel.forEach(function (f) { f(lid); });
  };
  lvlSel.addEventListener("change", function () { setGroup(lvlSel.value); });

  // ---------------------------------------------------------- practice builder (Joe's template sections)
  var B = document.querySelector("[data-builder]");
  var builder = null;
  if (B) {
    B.hidden = false;
    var bl = $("b-level"), s1 = $("b-skill1"), s2 = $("b-skill2"), rev = $("b-review"), dateIn = $("b-date"),
        sheet = $("b-sheet"), drillBox = $("b-drills"), revCount = $("b-review-count");
    var touched = false, plainText = "", bCur = null;
    var fillSelect = function (sel, lid, withNone) {
      sel.innerHTML = "";
      if (withNone) { var o = el("option", "None"); o.value = ""; sel.appendChild(o); }
      Object.keys(DATA.positions).forEach(function (pid) {
        var g = document.createElement("optgroup"); g.label = DATA.positions[pid];
        skillsFor(lid).filter(function (s) { return s.position === pid; }).forEach(function (s) { var o = el("option", s.name); o.value = s.id; g.appendChild(o); });
        sel.appendChild(g);
      });
    };
    var fillReview = function (lid) {
      rev.innerHTML = "";
      Object.keys(DATA.positions).forEach(function (pid) {
        rev.appendChild(el("p", DATA.positions[pid], "yc-checklist-h"));
        skillsFor(lid).filter(function (s) { return s.position === pid; }).forEach(function (s) {
          var lab = el("label"), cb = document.createElement("input");
          cb.type = "checkbox"; cb.value = s.id;
          cb.addEventListener("change", function () { touched = true; render(); });
          lab.appendChild(cb); lab.appendChild(document.createTextNode(" " + s.name)); rev.appendChild(lab);
        });
      });
    };
    var suggestReview = function () {
      var list = skillsFor(bl.value), picks = [s1.value, s2.value];
      var i = list.map(function (x) { return x.id; }).indexOf(s1.value);
      var sug = list.slice(Math.max(0, i - 3), i).map(function (x) { return x.id; });
      list.forEach(function (x) { if (sug.length < 3 && sug.indexOf(x.id) < 0 && picks.indexOf(x.id) < 0) sug.push(x.id); });
      rev.querySelectorAll("input").forEach(function (cb) { cb.checked = sug.indexOf(cb.value) >= 0 && picks.indexOf(cb.value) < 0; });
    };
    var render = function () {
      var lid = bl.value, L = DATA.levels[lid];
      var picks = [byId(s1.value), byId(s2.value)].filter(function (x, i, a) { return x && a.indexOf(x) === i; });
      var review = Array.prototype.slice.call(rev.querySelectorAll("input:checked")).map(function (cb) { return byId(cb.value); })
        .filter(function (x) { return picks.indexOf(x) < 0; });
      revCount.textContent = "(" + review.length + " selected)";
      var lives = [];
      picks.forEach(function (p) { if (p.live && lives.indexOf(p.live) < 0) lives.push(p.live); });
      lives.push(lid === "novice" ? "Quick starts (10–15 seconds)" : "Quick starts with a score given (down 1, down 2)");
      var moves = function (arr, isNew) { return arr.map(function (x) { return { t: x.name + (isNew ? " (new)" : ""), sub: x.teach }; }); };
      var plain = function (arr) { return arr.map(function (t) { return { t: t, sub: [] }; }); };
      var secs = [
        ["Announcements", plain(["Skin check and attendance"])],
        ["Warm-up", plain([L.warmup])],
        [L.drill, moves(review, false)],
        ["New Technique", moves(picks, true)],
        ["Contest situation", plain(lives.concat(["Matched by size and experience. Short goes."]))],
        ["Conditioning", plain([L.conditioning])],
        ["Announcements", plain([""])],
        ["Team Culture", plain([lid === "novice" ? "Observations: “What did you see someone do well?”" : "Spotlight", "Handshake line"])],
        ["My notes", plain(picks.map(function (p) { return p.name + ": " + p.demo; }).concat(["Who needs it re-taught next practice?"]))]
      ];
      var d = dateIn.value ? new Date(dateIn.value + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "numeric", day: "numeric", year: "2-digit" }) : "";
      sheet.innerHTML = "";
      var wrap = el("div", null, "yc-sheet"), head = el("div", null, "yc-sheet-head"), body = el("div", null, "yc-sheet-body");
      head.appendChild(el("h3", "Practice Plan")); head.appendChild(el("span", (d ? d + " · " : "") + L.name));
      var text = ["Practice Plan" + (d ? " – " + d : "") + " – " + L.name, ""];
      secs.forEach(function (sec) {
        var box = el("section"), ul = el("ul");
        box.appendChild(el("h4", sec[0])); text.push(sec[0] + ":");
        sec[1].forEach(function (it) {
          var li = el("li", it.t); text.push("  - " + it.t);
          if (it.sub && it.sub.length) {
            var sub = el("ul");
            it.sub.forEach(function (c) { sub.appendChild(el("li", c)); text.push("      - " + c); });
            li.appendChild(sub);
          }
          ul.appendChild(li);
        });
        box.appendChild(ul); body.appendChild(box);
      });
      wrap.appendChild(head); wrap.appendChild(body); sheet.appendChild(wrap);
      plainText = text.join("\n");
      // drills to run for the new technique
      drillBox.innerHTML = "";
      var ids = [];
      picks.forEach(function (p) { p.drills.forEach(function (x) { if (ids.indexOf(x) < 0) ids.push(x); }); });
      ids.forEach(function (x) {
        var dd = DATA.drills[x]; if (!dd) return;
        var item = el("div", null, "ycp-bdrill"), a = el("a", dd.name);
        a.href = "#drill-" + x; item.appendChild(a); item.appendChild(el("p", dd.cue, "ycp-small muted"));
        drillBox.appendChild(item);
      });
    };
    var setLevel = function (lid, skillId) {
      if (bCur !== lid) { bCur = lid; bl.value = lid; fillSelect(s1, lid, false); fillSelect(s2, lid, true); fillReview(lid); touched = false; }
      if (skillId) { s1.value = skillId; touched = false; }
      if (!touched) suggestReview();
      render();
    };
    bl.addEventListener("change", function () { setGroup(bl.value); });
    s1.addEventListener("change", function () { if (!touched) suggestReview(); render(); });
    s2.addEventListener("change", function () { if (!touched) suggestReview(); render(); });
    dateIn.addEventListener("change", render);
    onLevel.push(function (lid) { if (bCur !== lid) setLevel(lid); });
    $("b-print").addEventListener("click", function () {
      document.body.classList.add("print-plan"); window.print();
      setTimeout(function () { document.body.classList.remove("print-plan"); }, 500);
    });
    $("b-copy").addEventListener("click", function () { copy(plainText, this, "Copy plan"); });
    builder = { setLevel: setLevel };
  }
  document.querySelectorAll('a[href="#builder"][data-level]').forEach(function (a) {
    a.addEventListener("click", function () { setGroup(a.dataset.level); if (builder) builder.setLevel(a.dataset.level, a.dataset.skill); });
  });

  // ---------------------------------------------------------- drill library filters
  var F = document.querySelector("[data-drill-filters]");
  if (F) {
    F.hidden = false;
    var cards = Array.prototype.slice.call(document.querySelectorAll(".ycp-drill"));
    var fl = $("f-level"), fp = $("f-pos"), ft = $("f-type"), fc = $("f-count");
    var filt = function () {
      var n = 0;
      cards.forEach(function (c) {
        var ok = (!fl.value || c.dataset.levels.split(" ").indexOf(fl.value) >= 0) &&
                 (!fp.value || c.dataset.position === fp.value || c.dataset.position === "all") &&
                 (!ft.value || c.dataset.type === ft.value);
        c.hidden = !ok; if (ok) n++;
      });
      fc.textContent = "Showing " + n + " of " + cards.length + " drills, live situations and games.";
    };
    [fl, fp, ft].forEach(function (s) { s.addEventListener("change", filt); });
    filt();
    // a drill chip link clears filters so the drill is visible
    document.querySelectorAll('a[href^="#drill-"]').forEach(function (a) {
      a.addEventListener("click", function () { fl.value = ""; fp.value = ""; ft.value = ""; filt(); });
    });
  }
  document.querySelectorAll("[data-copy-drill]").forEach(function (b) {
    b.addEventListener("click", function () {
      var c = b.closest(".ycp-drill");
      var rows = Array.prototype.slice.call(c.querySelectorAll(".ycp-dl > div")).map(function (r) {
        return r.querySelector("dt").textContent + ": " + r.querySelector("dd").textContent;
      });
      copy(c.querySelector("h3").textContent + "\n" + rows.join("\n"), b, "Copy drill");
    });
  });

  // ---------------------------------------------------------- coaching challenge
  var Q = document.querySelector("[data-quiz]");
  if (Q && DATA.quiz.length) {
    Q.hidden = false;
    var qi = 0, score = 0;
    var showQ = function () {
      var q = DATA.quiz[qi];
      $("q-bar").style.width = ((qi + 1) / DATA.quiz.length * 100) + "%";
      $("q-num").textContent = "Scenario " + (qi + 1) + " / " + DATA.quiz.length;
      $("q-text").textContent = q.q;
      var box = $("q-opts"); box.innerHTML = "";
      $("q-fb").hidden = true; $("q-next").disabled = true;
      $("q-next").textContent = qi === DATA.quiz.length - 1 ? "See your result →" : "Next scenario →";
      q.options.forEach(function (o, i) {
        var b = el("button", String.fromCharCode(65 + i) + ". " + o, "ycp-opt"); b.type = "button";
        b.addEventListener("click", function () {
          if (!$("q-next").disabled) return;
          var right = i === q.answer; if (right) score++;
          box.querySelectorAll("button").forEach(function (x, j) {
            x.classList.toggle("right", j === q.answer); x.classList.toggle("wrong", j === i && !right); x.setAttribute("aria-disabled", "true");
          });
          var fb = $("q-fb"); fb.hidden = false; fb.className = "ycp-feedback " + (right ? "good" : "bad");
          fb.innerHTML = ""; fb.appendChild(el("b", right ? "That’s the Northampton way. " : "Not quite. ")); fb.appendChild(document.createTextNode(q.why));
          $("q-next").disabled = false;
        });
        box.appendChild(b);
      });
    };
    $("q-next").addEventListener("click", function () {
      if (qi < DATA.quiz.length - 1) { qi++; showQ(); return; }
      $("q-num").textContent = "Done";
      $("q-text").textContent = "You chose the Northampton way on " + score + " of " + DATA.quiz.length + " scenarios.";
      $("q-opts").innerHTML = ""; $("q-fb").hidden = true;
      var b = $("q-next"); b.textContent = "Start over"; b.disabled = false;
      b.onclick = function () { b.onclick = null; qi = 0; score = 0; showQ(); };
    });
    showQ();
  }

  // ---------------------------------------------------------- weekly check-in (stays on this device)
  var CK = document.querySelector("[data-checkin]");
  var cl = $("c-level");
  var renderCheck = null;
  if (CK) {
    CK.hidden = false;
    var items = function (lid) { return DATA.checkin.common.concat(DATA.checkin.levels[lid] || []); };
    renderCheck = function () {
      var lid = cl.value, key = "yc-checkin-" + lid, saved = [];
      try { saved = JSON.parse(store.get(key)) || []; } catch (e) { saved = []; }
      $("c-title").textContent = "After-practice reflection · " + DATA.levels[lid].name;
      var box = $("c-items"); box.innerHTML = "";
      var list = items(lid);
      var update = function () {
        var on = Array.prototype.slice.call(box.querySelectorAll("input")).filter(function (x) { return x.checked; }).length;
        $("c-count").textContent = on + " / " + list.length + " items checked";
        $("c-bar").style.width = (on / list.length * 100) + "%";
      };
      list.forEach(function (t, i) {
        var lab = el("label", null, "ycp-checkitem"), cb = document.createElement("input");
        cb.type = "checkbox"; cb.checked = saved.indexOf(i) >= 0;
        cb.addEventListener("change", function () {
          var now = []; box.querySelectorAll("input").forEach(function (x, j) { if (x.checked) now.push(j); });
          store.set(key, JSON.stringify(now)); update();
        });
        lab.appendChild(cb); lab.appendChild(el("span", t)); box.appendChild(lab);
      });
      update();
    };
    cl.addEventListener("change", renderCheck);
    $("c-reset").addEventListener("click", function () { store.del("yc-checkin-" + cl.value); renderCheck(); });
    $("c-copy").addEventListener("click", function () {
      var lid = cl.value, lines = ["Weekly check-in – " + DATA.levels[lid].name];
      $("c-items").querySelectorAll("label").forEach(function (l) {
        lines.push((l.querySelector("input").checked ? "[x] " : "[ ] ") + l.textContent);
      });
      copy(lines.join("\n"), this, "Copy check-in summary");
    });
    onLevel.push(function (lid) { cl.value = lid; renderCheck(); });
  }

  // ---------------------------------------------------------- section bar: highlight where you are
  var tabLinks = Array.prototype.slice.call(document.querySelectorAll(".ycp-tabs a"));
  if ("IntersectionObserver" in window && tabLinks.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) tabLinks.forEach(function (a) { a.classList.toggle("on", a.getAttribute("href") === "#" + en.target.id); });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    tabLinks.forEach(function (a) { var t = document.querySelector(a.getAttribute("href")); if (t) io.observe(t); });
  }

  // ---------------------------------------------------------- start-up
  // #novice / #orange-black (or a position or skill inside one) picks the group
  var fromHash = function () {
    var h = location.hash.slice(1);
    var lid = levels.filter(function (x) { return h === x || h.indexOf(x + "-") === 0; })[0];
    if (!lid) return false;
    setGroup(lid);
    var target = document.getElementById(h);
    if (target) {
      var d = target.tagName === "DETAILS" ? target : target.closest("details");
      if (d) d.open = true;
      (target.tagName === "ARTICLE" || target.tagName === "DETAILS" ? target : $("expectations")).scrollIntoView();
    }
    return true;
  };
  if (!fromHash()) setGroup(store.get("yc-level") || levels[0]);
  window.addEventListener("hashchange", fromHash);
})();
