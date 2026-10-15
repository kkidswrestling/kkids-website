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

  // ---------------------------------------------------------- practice builder (Joe's template sections, editable)
  // The plan is a list of sections. Choices at the top fill the sections; any section the coach
  // edits keeps the coach's version (with a Reset link). The plan saves on this device.
  var B = document.querySelector("[data-builder]");
  var builder = null;
  if (B) {
    B.hidden = false;
    var bl = $("b-level"), s1 = $("b-skill1"), s2 = $("b-skill2"), rev = $("b-review"), dateIn = $("b-date"),
        sheet = $("b-sheet"), drillBox = $("b-drills"), revCount = $("b-review-count");
    var touched = false, bCur = null, plan = null, PKEY = "yc-plan";
    var SECTIONS = ["announce", "warmup", "drill", "new", "contest", "cond", "announce2", "culture", "notes"];
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
          cb.addEventListener("change", function () { touched = true; refresh(); });
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
    var picksNow = function () { return [byId(s1.value), byId(s2.value)].filter(function (x, i, a) { return x && a.indexOf(x) === i; }); };
    var reviewNow = function () {
      var picks = picksNow();
      return Array.prototype.slice.call(rev.querySelectorAll("input:checked")).map(function (cb) { return byId(cb.value); })
        .filter(function (x) { return picks.indexOf(x) < 0; });
    };
    var it = function (t, sub) { return { t: t, sub: (sub || []).slice() }; };
    // what each section suggests from the current choices
    var suggest = function (key) {
      var lid = bl.value, L = DATA.levels[lid], picks = picksNow();
      if (key === "announce") return [it("Skin check and attendance")];
      if (key === "warmup") return [it(L.warmup)];
      if (key === "drill") return reviewNow().map(function (x) { return it(x.name, x.teach); });
      if (key === "new") return picks.map(function (x) { return it(x.name + " (new)", x.teach); });
      if (key === "contest") {
        var lives = [];
        picks.forEach(function (p) { if (p.live && lives.indexOf(p.live) < 0) lives.push(p.live); });
        lives.push(lid === "novice" ? "Quick starts (10–15 seconds)" : "Quick starts with a score given (down 1, down 2)");
        return lives.concat(["Matched by size and experience. Short goes."]).map(function (t) { return it(t); });
      }
      if (key === "cond") return [it(L.conditioning)];
      if (key === "announce2") return [it("")];
      if (key === "culture") return [it(lid === "novice" ? "Observations: “What did you see someone do well?”" : "Spotlight"), it("Handshake line")];
      if (key === "notes") return picks.map(function (p) { return it(p.name + ": " + p.demo); }).concat([it("Who needs it re-taught next practice?")]);
      return [];
    };
    var title = function (key) {
      return { announce: "Announcements", warmup: "Warm-up", drill: DATA.levels[bl.value].drill, "new": "New Technique",
               contest: "Contest situation", cond: "Conditioning", announce2: "Announcements", culture: "Team Culture", notes: "My notes" }[key];
    };
    var save = function () {
      plan.level = bl.value; plan.date = dateIn.value; plan.s1 = s1.value; plan.s2 = s2.value;
      plan.review = Array.prototype.slice.call(rev.querySelectorAll("input:checked")).map(function (cb) { return cb.value; });
      plan.touched = touched;
      store.set(PKEY, JSON.stringify(plan));
    };
    var newPlan = function () { return { sections: SECTIONS.map(function (k) { return { key: k, items: suggest(k), custom: false }; }) }; };
    // re-fill every section the coach hasn't edited
    var refresh = function () {
      if (!plan) plan = newPlan();
      plan.sections.forEach(function (sec) { if (!sec.custom) sec.items = suggest(sec.key); });
      draw(); save();
    };
    var editable = function (node, onEdit) {
      node.contentEditable = "true"; node.spellcheck = true; node.className = (node.className + " ycp-ed").trim();
      node.addEventListener("input", function () { onEdit(node.textContent); });
      node.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); node.blur(); } });
    };
    var adders = function (sec) {
      var lid = bl.value, opts = [];
      if (sec.key === "warmup" || sec.key === "cond") {
        Object.keys(DATA.drills).forEach(function (k) { var d = DATA.drills[k]; if (d.type === "game" && d.levels.indexOf(lid) >= 0) opts.push(d.name); });
      } else if (sec.key === "contest") {
        Object.keys(DATA.drills).forEach(function (k) { var d = DATA.drills[k]; if (d.type === "live" && d.levels.indexOf(lid) >= 0) opts.push(d.name); });
        (DATA.live[lid] || []).forEach(function (t) { if (opts.indexOf(t) < 0) opts.push(t); });
      } else if (sec.key === "drill" || sec.key === "new") {
        skillsFor(lid).forEach(function (x) { opts.push(x.name); });
      }
      return opts;
    };
    var draw = function () {
      var lid = bl.value, L = DATA.levels[lid];
      var d = dateIn.value ? new Date(dateIn.value + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "numeric", day: "numeric", year: "2-digit" }) : "";
      sheet.innerHTML = "";
      var wrap = el("div", null, "yc-sheet editable"), head = el("div", null, "yc-sheet-head"), body = el("div", null, "yc-sheet-body");
      head.appendChild(el("h3", "Practice Plan")); head.appendChild(el("span", (d ? d + " · " : "") + L.name));
      plan.sections.forEach(function (sec) {
        var box = el("section"), h = el("h4", title(sec.key)), ul = el("ul");
        if (sec.custom) {
          var rs = el("button", "↺ Reset", "ycp-reset"); rs.type = "button"; rs.title = "Go back to the suggested lines";
          rs.addEventListener("click", function () { sec.custom = false; refresh(); });
          h.appendChild(rs);
        }
        box.appendChild(h);
        sec.items.forEach(function (item, ii) {
          var li = el("li"), txt = el("span", item.t);
          editable(txt, function (v) { item.t = v; sec.custom = true; save(); });
          var x = el("button", "×", "ycp-x"); x.type = "button"; x.setAttribute("aria-label", "Remove this line");
          x.addEventListener("click", function () { sec.items.splice(ii, 1); sec.custom = true; draw(); save(); });
          li.appendChild(txt); li.appendChild(x);
          if (item.sub.length) {
            var sub = el("ul");
            item.sub.forEach(function (c, ci) {
              var sl = el("li"), st = el("span", c);
              editable(st, function (v) { item.sub[ci] = v; sec.custom = true; save(); });
              var sx = el("button", "×", "ycp-x"); sx.type = "button"; sx.setAttribute("aria-label", "Remove this cue");
              sx.addEventListener("click", function () { item.sub.splice(ci, 1); sec.custom = true; draw(); save(); });
              sl.appendChild(st); sl.appendChild(sx); sub.appendChild(sl);
            });
            li.appendChild(sub);
          }
          ul.appendChild(li);
        });
        box.appendChild(ul);
        var tools = el("div", null, "ycp-sec-tools");
        var add = el("button", "+ Add line", "ycp-add"); add.type = "button";
        add.addEventListener("click", function () {
          sec.items.push(it("")); sec.custom = true; draw(); save();
          var spans = sheet.querySelectorAll("section")[plan.sections.indexOf(sec)].querySelectorAll(":scope > ul > li > span");
          if (spans.length) spans[spans.length - 1].focus();
        });
        tools.appendChild(add);
        var opts = adders(sec);
        if (opts.length) {
          var pick = el("select", null, "ycp-pick");
          var lab = sec.key === "contest" ? "+ Add a live situation…" : (sec.key === "drill" || sec.key === "new") ? "+ Add a skill…" : "+ Add a game…";
          var o0 = el("option", lab); o0.value = ""; pick.appendChild(o0);
          opts.forEach(function (t) { var o = el("option", t); o.value = t; pick.appendChild(o); });
          pick.setAttribute("aria-label", lab.replace("+ ", "").replace("…", ""));
          pick.addEventListener("change", function () {
            if (!pick.value) return;
            var sk = skillsFor(bl.value).filter(function (x) { return x.name === pick.value; })[0];
            sec.items.push(sk ? it(sk.name + (sec.key === "new" ? " (new)" : ""), sk.teach) : it(pick.value));
            sec.custom = true; draw(); save();
          });
          tools.appendChild(pick);
        }
        box.appendChild(tools);
        body.appendChild(box);
      });
      wrap.appendChild(head); wrap.appendChild(body); sheet.appendChild(wrap);
      // drills to run for the new technique
      drillBox.innerHTML = "";
      var ids = [];
      picksNow().forEach(function (p) { p.drills.forEach(function (x) { if (ids.indexOf(x) < 0) ids.push(x); }); });
      ids.forEach(function (x) {
        var dd = DATA.drills[x]; if (!dd) return;
        var item = el("div", null, "ycp-bdrill"), a = el("a", dd.name);
        a.href = "#drill-" + x; item.appendChild(a); item.appendChild(el("p", dd.cue, "ycp-small muted"));
        drillBox.appendChild(item);
      });
      revCount.textContent = "(" + reviewNow().length + " selected)";
    };
    var planText = function () {
      var d = dateIn.value ? new Date(dateIn.value + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "numeric", day: "numeric", year: "2-digit" }) : "";
      var out = ["Practice Plan" + (d ? " – " + d : "") + " – " + DATA.levels[bl.value].name, ""];
      plan.sections.forEach(function (sec) {
        out.push(title(sec.key) + ":");
        sec.items.forEach(function (i) { out.push("  - " + i.t); i.sub.forEach(function (c) { out.push("      - " + c); }); });
      });
      return out.join("\n");
    };
    var setLevel = function (lid, skillId) {
      var changed = bCur !== lid;
      if (changed) { bCur = lid; bl.value = lid; fillSelect(s1, lid, false); fillSelect(s2, lid, true); fillReview(lid); touched = false; }
      if (skillId) { s1.value = skillId; touched = false; }
      if (!touched) suggestReview();
      if (changed || skillId) plan = newPlan();
      refresh();
    };
    bl.addEventListener("change", function () { setGroup(bl.value); });
    s1.addEventListener("change", function () { if (!touched) suggestReview(); refresh(); });
    s2.addEventListener("change", function () { if (!touched) suggestReview(); refresh(); });
    dateIn.addEventListener("change", function () { draw(); save(); });
    $("b-fresh").addEventListener("click", function () {
      store.del(PKEY); touched = false; suggestReview(); plan = newPlan(); refresh();
    });
    onLevel.push(function (lid) { if (bCur !== lid) setLevel(lid); });
    $("b-print").addEventListener("click", function () {
      document.body.classList.add("print-plan"); window.print();
      setTimeout(function () { document.body.classList.remove("print-plan"); }, 500);
    });
    $("b-copy").addEventListener("click", function () { copy(planText(), this, "Copy plan"); });
    // restore a saved plan for this device
    var restore = function () {
      var saved = null;
      try { saved = JSON.parse(store.get(PKEY)); } catch (e) { saved = null; }
      if (!saved || !saved.sections || levels.indexOf(saved.level) < 0) return false;
      bCur = saved.level; bl.value = saved.level; fillSelect(s1, saved.level, false); fillSelect(s2, saved.level, true); fillReview(saved.level);
      if (saved.s1) s1.value = saved.s1; s2.value = saved.s2 || "";
      rev.querySelectorAll("input").forEach(function (cb) { cb.checked = (saved.review || []).indexOf(cb.value) >= 0; });
      dateIn.value = saved.date || ""; touched = !!saved.touched; plan = { sections: saved.sections };
      return true;
    };
    builder = { setLevel: setLevel, restore: restore, refresh: refresh };
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
  var restored = builder ? builder.restore() : false;
  if (!fromHash()) setGroup(restored ? bCur : (store.get("yc-level") || levels[0]));
  if (restored && builder) builder.refresh();
  window.addEventListener("hashchange", fromHash);
})();
