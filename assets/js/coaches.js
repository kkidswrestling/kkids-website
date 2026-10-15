/* Youth Coaches' Playbook: Novice / Orange & Black switch.
   Without JS both groups show, one after the other. */
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.yc-tabs [role="tab"]'));
  if (!tabs.length) return;
  var KEY = "yc-level";
  var select = function (tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
    try { localStorage.setItem(KEY, tab.dataset.level); } catch (e) {}
  };
  var byLevel = function (lid) { return tabs.filter(function (t) { return t.dataset.level === lid; })[0]; };
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () {
      select(t);
      if (history.replaceState) history.replaceState(null, "", "#" + t.dataset.level);
    });
    t.addEventListener("keydown", function (e) {
      var n = null;
      if (e.key === "ArrowRight") n = tabs[(i + 1) % tabs.length];
      if (e.key === "ArrowLeft") n = tabs[(i - 1 + tabs.length) % tabs.length];
      if (e.key === "Home") n = tabs[0];
      if (e.key === "End") n = tabs[tabs.length - 1];
      if (n) { e.preventDefault(); select(n, true); }
    });
  });
  // #novice or #orange-black in the address picks the group (a position anchor like #novice-top too)
  var fromHash = function () {
    var h = location.hash.slice(1);
    var t = tabs.filter(function (x) { return h === x.dataset.level || h.indexOf(x.dataset.level + "-") === 0; })[0];
    if (t) {
      select(t);
      var target = document.getElementById(h);
      if (target && target.tagName === "DETAILS") { target.open = true; target.scrollIntoView(); }
      else document.getElementById("curriculum").scrollIntoView();
      return true;
    }
    return false;
  };
  if (!fromHash()) {
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    select(byLevel(saved) || tabs[0]);
  }
  window.addEventListener("hashchange", fromHash);
})();
