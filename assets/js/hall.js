/* Hall of Champions: record-book tabs and wrestler search */
(function () {
  "use strict";

  // Tabs (arrow keys move between tabs)
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tabs [role="tab"]'));
  var select = function (tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
  };
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { select(t); });
    t.addEventListener("keydown", function (e) {
      var n = null;
      if (e.key === "ArrowRight") n = tabs[(i + 1) % tabs.length];
      if (e.key === "ArrowLeft") n = tabs[(i - 1 + tabs.length) % tabs.length];
      if (e.key === "Home") n = tabs[0];
      if (e.key === "End") n = tabs[tabs.length - 1];
      if (n) { e.preventDefault(); select(n, true); }
    });
  });

  // Search
  var q = document.getElementById("q");
  var out = document.getElementById("results");
  if (!q || !out) return;
  var people = [];
  var src = document.querySelector('script[src$="hall.js"]').getAttribute("src").replace(/assets\/js\/hall\.js$/, "");
  fetch(src + "assets/data/hall.json").then(function (r) { return r.json(); }).then(function (d) { people = d; run(); });

  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var times = function (n, word) { return n === 1 ? word : n + "x " + word; };

  var summary = function (p) {
    var c = { state: 0, medal: 0, reg: 0, dist: 0 };
    p.honors.forEach(function (h) {
      if (h[1] === "PIAA champion") { c.state++; c.medal++; }
      else if (/^PIAA \d/.test(h[1])) c.medal++;
      else if (h[1] === "Northeast Regional champion") c.reg++;
      else if (h[1] === "District XI champion") c.dist++;
    });
    var bits = [];
    if (c.state) bits.push(times(c.state, "PIAA champion"));
    if (c.medal) bits.push(times(c.medal, "state medalist"));
    if (c.reg) bits.push(times(c.reg, "Regional champion"));
    if (c.dist) bits.push(times(c.dist, "District XI champion"));
    return bits.join(", ");
  };

  var filterTables = function (v) {
    document.querySelectorAll("table.hall").forEach(function (t) {
      var any = false;
      t.querySelectorAll("tbody tr").forEach(function (tr) {
        var name = (tr.dataset.name || tr.textContent).toLowerCase();
        var show = !v || name.indexOf(v) > -1 || tr.textContent.toLowerCase().indexOf(v) > -1;
        tr.hidden = !show;
        if (show) any = true;
      });
      var wrap = t.parentNode, note = wrap.querySelector(".hall-empty");
      if (!any && !note) { note = document.createElement("p"); note.className = "hall-empty"; wrap.appendChild(note); }
      if (note) { note.hidden = any; note.textContent = "No one on this list matches “" + v + "”."; }
    });
  };

  var run = function () {
    var v = q.value.trim().toLowerCase();
    filterTables(v);
    if (v.length < 2) { out.innerHTML = ""; return; }
    var hits = people.filter(function (p) { return p.name.toLowerCase().indexOf(v) > -1; }).slice(0, 8);
    if (!hits.length) {
      out.innerHTML = '<p class="none">No wrestler named “' + esc(q.value.trim()) + '” is on the champion lists yet.</p>';
      return;
    }
    out.innerHTML = hits.map(function (p) {
      var items = p.honors.map(function (h) {
        return "<li><b>" + h[0] + "</b><span>" + esc(h[1]) + "</span>" + (h[2] ? '<span class="w">' + esc(h[2]) + "</span>" : "") + "</li>";
      }).join("");
      var s = summary(p);
      return '<article class="profile"><h3>' + esc(p.name) + "</h3>" + (s ? '<p class="sum">' + esc(s) + "</p>" : "") + "<ul>" + items + "</ul></article>";
    }).join("");
  };
  var t = null;
  q.addEventListener("input", function () { clearTimeout(t); t = setTimeout(run, 120); });
  var param = new URLSearchParams(location.search).get("q");
  if (param) { q.value = param; }
})();
