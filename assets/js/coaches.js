/* Youth Coaches' Playbook: Novice / Orange & Black switch and the practice builder.
   Without JS both groups show one after the other and the builder stays hidden
   (the static practice template below it still shows). */
(function () {
  var dataEl = document.getElementById("yc-data");
  var DATA = dataEl ? JSON.parse(dataEl.textContent) : null;
  var KEY = "yc-level";
  var store = {
    get: function () { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set: function (v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  };

  // ---------------------------------------------------------- group tabs
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.yc-tabs [role="tab"]'));
  var onLevel = [];
  var selectTab = function (lid, focus) {
    var tab = tabs.filter(function (t) { return t.dataset.level === lid; })[0] || tabs[0];
    if (!tab) return;
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
    store.set(tab.dataset.level);
    onLevel.forEach(function (f) { f(tab.dataset.level); });
  };
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { selectTab(t.dataset.level); });
    t.addEventListener("keydown", function (e) {
      var n = null;
      if (e.key === "ArrowRight") n = tabs[(i + 1) % tabs.length];
      if (e.key === "ArrowLeft") n = tabs[(i - 1 + tabs.length) % tabs.length];
      if (e.key === "Home") n = tabs[0];
      if (e.key === "End") n = tabs[tabs.length - 1];
      if (n) { e.preventDefault(); selectTab(n.dataset.level, true); }
    });
  });

  // ---------------------------------------------------------- practice builder
  // Builds a plan in the layout of Joe's practice-plan template (same sections, same order).
  var B = document.querySelector("[data-builder]");
  if (B && DATA) {
    B.hidden = false;
    var $ = function (id) { return document.getElementById(id); };
    var lvlSel = $("b-level"), s1 = $("b-skill1"), s2 = $("b-skill2"), rev = $("b-review"), dateIn = $("b-date"), sheet = $("b-sheet");
    var touched = false, plainText = "", current = null;
    var skillsFor = function (lid) { return DATA.skills.filter(function (s) { return s.level === lid; }); };
    var byId = function (id) { return DATA.skills.filter(function (s) { return s.id === id; })[0]; };
    var el = function (tag, text, cls) { var n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; };
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
      var list = skillsFor(lvlSel.value), picks = [s1.value, s2.value];
      var i = list.map(function (x) { return x.id; }).indexOf(s1.value);
      var sug = list.slice(Math.max(0, i - 3), i).map(function (x) { return x.id; });
      list.forEach(function (x) { if (sug.length < 3 && sug.indexOf(x.id) < 0 && picks.indexOf(x.id) < 0) sug.push(x.id); });
      rev.querySelectorAll("input").forEach(function (cb) { cb.checked = sug.indexOf(cb.value) >= 0 && picks.indexOf(cb.value) < 0; });
    };
    var render = function () {
      var lid = lvlSel.value, L = DATA.levels[lid];
      var picks = [byId(s1.value), byId(s2.value)].filter(function (x, i, a) { return x && a.indexOf(x) === i; });
      var review = Array.prototype.slice.call(rev.querySelectorAll("input:checked")).map(function (cb) { return byId(cb.value); })
        .filter(function (x) { return picks.indexOf(x) < 0; });
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
    };
    var setLevel = function (lid, skillId) {
      if (current !== lid) { current = lid; lvlSel.value = lid; fillSelect(s1, lid, false); fillSelect(s2, lid, true); fillReview(lid); touched = false; }
      if (skillId) { s1.value = skillId; touched = false; }
      if (!touched) suggestReview();
      render();
    };
    lvlSel.addEventListener("change", function () { selectTab(lvlSel.value); });
    s1.addEventListener("change", function () { if (!touched) suggestReview(); render(); });
    s2.addEventListener("change", function () { if (!touched) suggestReview(); render(); });
    dateIn.addEventListener("change", render);
    onLevel.push(function (lid) { if (current !== lid) setLevel(lid); });
    $("b-print").addEventListener("click", function () {
      document.body.classList.add("print-plan");
      window.print();
      setTimeout(function () { document.body.classList.remove("print-plan"); }, 500);
    });
    $("b-copy").addEventListener("click", function () {
      var btn = this;
      if (navigator.clipboard) navigator.clipboard.writeText(plainText).then(function () {
        btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy plan"; }, 1600);
      }, function () {});
    });
    document.querySelectorAll('a[href="#builder"][data-level]').forEach(function (a) {
      a.addEventListener("click", function () { selectTab(a.dataset.level); setLevel(a.dataset.level, a.dataset.skill); });
    });
  }

  // ---------------------------------------------------------- start-up
  // #novice / #orange-black (or a position or skill inside one) picks the group
  var fromHash = function () {
    var h = location.hash.slice(1);
    var t = tabs.filter(function (x) { return h === x.dataset.level || h.indexOf(x.dataset.level + "-") === 0; })[0];
    if (!t) return false;
    selectTab(t.dataset.level);
    var target = document.getElementById(h);
    if (target) {
      var d = target.tagName === "DETAILS" ? target : target.closest("details");
      if (d) d.open = true;
      (target.tagName === "ARTICLE" || target.tagName === "DETAILS" ? target : document.getElementById("curriculum")).scrollIntoView();
    }
    return true;
  };
  if (!fromHash()) selectTab(store.get() || (tabs[0] && tabs[0].dataset.level));
  window.addEventListener("hashchange", fromHash);
})();
