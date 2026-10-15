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
  var B = document.querySelector("[data-builder]");
  var builder = null;
  if (B && DATA) {
    B.hidden = false;
    var $ = function (id) { return document.getElementById(id); };
    var lvlSel = $("b-level"), s1 = $("b-skill1"), s2 = $("b-skill2"), out = $("b-plan"), title = $("b-title");
    var skillsFor = function (lid) { return DATA.skills.filter(function (s) { return s.level === lid; }); };
    var byId = function (id) { return DATA.skills.filter(function (s) { return s.id === id; })[0]; };
    var fill = function (sel, lid, withNone) {
      sel.innerHTML = "";
      if (withNone) { var o = document.createElement("option"); o.value = ""; o.textContent = "None"; sel.appendChild(o); }
      Object.keys(DATA.positions).forEach(function (pid) {
        var g = document.createElement("optgroup"); g.label = DATA.positions[pid];
        skillsFor(lid).filter(function (s) { return s.position === pid; }).forEach(function (s) {
          var o = document.createElement("option"); o.value = s.id; o.textContent = s.name; g.appendChild(o);
        });
        sel.appendChild(g);
      });
    };
    var tpl = {}; DATA.template.forEach(function (r) { tpl[r[0]] = r[1]; });
    var render = function () {
      var lid = lvlSel.value, L = DATA.levels[lid];
      var picks = [byId(s1.value), byId(s2.value)].filter(function (x, i, a) { return x && a.indexOf(x) === i; });
      var list = skillsFor(lid);
      var first = list.indexOf(picks[0]);
      var review = list.slice(Math.max(0, first - 3), first).filter(function (x) { return picks.indexOf(x) < 0; });
      if (review.length < 3) review = review.concat(list.filter(function (x) { return picks.indexOf(x) < 0 && review.indexOf(x) < 0; }).slice(0, 3 - review.length));
      var names = function (arr) { return arr.map(function (x) { return x.name; }).join(", "); };
      var lives = [];
      picks.forEach(function (p) { if (p.live && lives.indexOf(p.live) < 0) lives.push(p.live); });
      var blocks = [
        ["Skin check and attendance", tpl["Skin check and attendance"]],
        ["Warm-up and games", L.warmup],
        ["Review (2&2)", "3–5 skills already taught. Suggested: " + names(review) + "."],
        ["New technique", picks.map(function (p) { return p.name + " (new): " + (p.teach.length ? p.teach.join(" ") : "demonstrate it, then walk it through at half speed."); }).join("  ")],
        ["Drill", picks.map(function (p) { return p.drill; }).join(" ") + " Partners matched by size."],
        ["Live situations", (lives.length ? lives.join(" ") : "Quick starts.") + " Matched by size and experience. Short goes."],
        ["Conditioning game", L.conditioning],
        ["Team close", tpl["Team close"]],
        ["Coach's notes", "Can each wrestler demonstrate it? " + picks.map(function (p) { return p.name + ": " + p.demo.charAt(0).toLowerCase() + p.demo.slice(1); }).join(" ") + " Who needs it re-taught next practice?"]
      ];
      title.textContent = L.name + " practice: " + names(picks);
      out.innerHTML = "";
      blocks.forEach(function (b) {
        var li = document.createElement("li"), h = document.createElement("b"), p = document.createElement("span");
        h.textContent = b[0]; p.textContent = b[1]; li.appendChild(h); li.appendChild(p); out.appendChild(li);
      });
      builder.text = title.textContent + "\n\n" + blocks.map(function (b, i) { return (i + 1) + ". " + b[0] + ": " + b[1]; }).join("\n");
    };
    var setLevel = function (lid, skillId) {
      if (lvlSel.value !== lid || !s1.options.length) { lvlSel.value = lid; fill(s1, lid, false); fill(s2, lid, true); }
      if (skillId) s1.value = skillId;
      render();
    };
    builder = { setLevel: setLevel, text: "" };
    lvlSel.addEventListener("change", function () { selectTab(lvlSel.value); });
    s1.addEventListener("change", render);
    s2.addEventListener("change", render);
    onLevel.push(function (lid) { if (lvlSel.value !== lid || !s1.options.length) setLevel(lid); });
    $("b-print").addEventListener("click", function () {
      document.body.classList.add("print-plan");
      window.print();
      setTimeout(function () { document.body.classList.remove("print-plan"); }, 500);
    });
    $("b-copy").addEventListener("click", function () {
      var btn = this, done = function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy plan"; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(builder.text).then(done, function () {});
    });
    // "Build a practice" links on skill cards and level banners
    document.querySelectorAll('a[href="#builder"][data-level]').forEach(function (a) {
      a.addEventListener("click", function () {
        selectTab(a.dataset.level);
        setLevel(a.dataset.level, a.dataset.skill);
      });
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
