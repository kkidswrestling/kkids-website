/* Northampton Wrestling: menu, lightbox, sortable tables, chart tooltips */
(function () {
  "use strict";

  // Year in footer
  document.querySelectorAll("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  // Mobile menu
  var btn = document.querySelector(".menu-btn");
  var nav = document.getElementById("site-nav");
  if (btn && nav) {
    var setOpen = function (open) {
      btn.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("open", open);
      document.body.classList.toggle("nav-open", open);
      btn.querySelector(".label").textContent = open ? "Close" : "Menu";
    };
    btn.addEventListener("click", function () { setOpen(btn.getAttribute("aria-expanded") !== "true"); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") { setOpen(false); btn.focus(); }
    });
    window.matchMedia("(min-width: 1061px)").addEventListener("change", function (m) { if (m.matches) setOpen(false); });
  }


  // Dropdown menus (click/tap; hover handled in CSS on desktop)
  var subBtns = Array.prototype.slice.call(document.querySelectorAll(".sub-btn"));
  subBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      var open = b.getAttribute("aria-expanded") === "true";
      subBtns.forEach(function (x) { x.setAttribute("aria-expanded", "false"); });
      b.setAttribute("aria-expanded", String(!open));
    });
  });
  document.addEventListener("click", function (ev) {
    if (!ev.target.closest(".has-sub")) subBtns.forEach(function (x) { x.setAttribute("aria-expanded", "false"); });
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      var openBtn = subBtns.filter(function (x) { return x.getAttribute("aria-expanded") === "true"; })[0];
      if (openBtn) { openBtn.setAttribute("aria-expanded", "false"); openBtn.focus(); }
    }
  });

  // Roster carousel buttons
  document.querySelectorAll("[data-carousel]").forEach(function (c) {
    var track = c.querySelector(".car-track");
    c.querySelectorAll(".car-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        track.scrollBy({ left: Number(b.dataset.dir) * track.clientWidth * 0.8, behavior: "smooth" });
      });
    });
  });

  // Count-up numbers (once, when they scroll into view)
  var counts = document.querySelectorAll(".count");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (counts.length && "IntersectionObserver" in window && !reduce) {
    counts.forEach(function (el) { el.textContent = "0"; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        io.unobserve(en.target);
        var el = en.target, to = Number(el.dataset.to), t0 = null, dur = 1400;
        var step = function (ts) {
          if (!t0) t0 = ts;
          var p = Math.min(1, (ts - t0) / dur), eased = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(to * eased).toLocaleString();
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    }, { threshold: 0.4 });
    counts.forEach(function (el) { io.observe(el); });
  }

  // YouTube playlist: load the player only when asked
  document.querySelectorAll(".video-facade[data-yt]").forEach(function (v) {
    var b = v.querySelector(".vf-play");
    b.addEventListener("click", function () {
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/videoseries?list=" + encodeURIComponent(v.dataset.yt) + "&autoplay=1";
      f.title = "Northampton Wrestling video playlist";
      f.allow = "autoplay; encrypted-media; picture-in-picture";
      f.allowFullscreen = true;
      v.innerHTML = "";
      v.appendChild(f);
    });
  });

  // Single YouTube video (champion pages)
  document.querySelectorAll(".video-facade[data-ytv]").forEach(function (v) {
    v.querySelector(".vf-play").addEventListener("click", function () {
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(v.dataset.ytv) + "?autoplay=1&rel=0" +
        (v.dataset.start ? "&start=" + Number(v.dataset.start) : "") + (v.dataset.end ? "&end=" + Number(v.dataset.end) : "");
      f.title = "State final video";
      f.allow = "autoplay; encrypted-media; picture-in-picture";
      f.allowFullscreen = true;
      v.innerHTML = "";
      v.appendChild(f);
    });
  });

  // Timeline: highlight the decade in view
  var tlLinks = document.querySelectorAll(".tl-nav a");
  if (tlLinks.length && "IntersectionObserver" in window) {
    var tio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) tlLinks.forEach(function (a) { a.classList.toggle("on", a.getAttribute("href") === "#" + en.target.id); });
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    document.querySelectorAll(".tl-decade").forEach(function (d) { tio.observe(d); });
  }

  // Lightbox for [data-lightbox] galleries
  var links = Array.prototype.slice.call(document.querySelectorAll("a[data-lightbox]"));
  if (links.length && "HTMLDialogElement" in window) {
    var dlg = document.createElement("dialog");
    dlg.className = "lightbox";
    dlg.setAttribute("aria-label", "Photo viewer");
    dlg.innerHTML =
      '<div class="lb-inner"><div class="lb-bar"><span class="lb-count" aria-live="polite"></span>' +
      '<button type="button" class="lb-btn lb-close">Close</button></div>' +
      '<div class="lb-stage"><button type="button" class="lb-btn lb-nav lb-prev" aria-label="Previous photo">‹</button>' +
      '<img alt=""><button type="button" class="lb-btn lb-nav lb-next" aria-label="Next photo">›</button></div>' +
      '<p class="lb-cap"></p></div>';
    document.body.appendChild(dlg);
    var img = dlg.querySelector("img"), cap = dlg.querySelector(".lb-cap"), count = dlg.querySelector(".lb-count");
    var group = [], idx = 0, opener = null;
    var show = function (i) {
      idx = (i + group.length) % group.length;
      var a = group[idx];
      img.src = a.getAttribute("href");
      img.alt = a.querySelector("img").alt;
      cap.textContent = a.dataset.caption || "";
      count.textContent = "Photo " + (idx + 1) + " of " + group.length;
    };
    links.forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        opener = a;
        group = links.filter(function (x) { return x.dataset.lightbox === a.dataset.lightbox; });
        show(group.indexOf(a));
        dlg.showModal();
      });
    });
    dlg.querySelector(".lb-close").addEventListener("click", function () { dlg.close(); });
    dlg.querySelector(".lb-prev").addEventListener("click", function () { show(idx - 1); });
    dlg.querySelector(".lb-next").addEventListener("click", function () { show(idx + 1); });
    dlg.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") show(idx - 1);
      if (e.key === "ArrowRight") show(idx + 1);
    });
    dlg.addEventListener("click", function (e) { if (e.target === dlg || e.target.classList.contains("lb-stage")) dlg.close(); });
    dlg.addEventListener("close", function () { img.removeAttribute("src"); if (opener) opener.focus(); });
    var sx = null;
    dlg.addEventListener("touchstart", function (e) { sx = e.touches[0].clientX; }, { passive: true });
    dlg.addEventListener("touchend", function (e) {
      if (sx === null) return;
      var dx = e.changedTouches[0].clientX - sx;
      if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
      sx = null;
    });
  }

  // Sortable tables
  document.querySelectorAll("table.sortable").forEach(function (table) {
    var ths = table.querySelectorAll("thead th");
    ths.forEach(function (th, col) {
      var b = th.querySelector("button");
      if (!b) return;
      b.addEventListener("click", function () {
        var cur = th.getAttribute("aria-sort");
        var dir = cur === "descending" ? "ascending" : "descending";
        if (col === 0 && cur === "none") dir = "ascending";
        ths.forEach(function (t) { t.setAttribute("aria-sort", "none"); });
        th.setAttribute("aria-sort", dir);
        var body = table.tBodies[0];
        var rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (r1, r2) {
          var a = r1.cells[col].dataset.v, c = r2.cells[col].dataset.v;
          var na = parseFloat(a), nc = parseFloat(c);
          var cmp = (!isNaN(na) && !isNaN(nc)) ? na - nc : String(a).localeCompare(String(c));
          return dir === "ascending" ? cmp : -cmp;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });

  // Chart tooltips
  document.querySelectorAll(".chart-box").forEach(function (box) {
    var tip = box.querySelector(".tip");
    var svg = box.querySelector("svg");
    box.querySelectorAll(".bar").forEach(function (g) {
      var place = function () {
        var r = g.querySelector("path").getBoundingClientRect(), br = box.getBoundingClientRect();
        tip.textContent = g.dataset.tip;
        tip.style.left = (r.left - br.left + r.width / 2) + "px";
        tip.style.top = (r.top - br.top - 4) + "px";
        tip.hidden = false;
      };
      g.addEventListener("mouseenter", place);
      g.addEventListener("focus", place);
      g.addEventListener("mouseleave", function () { tip.hidden = true; });
      g.addEventListener("blur", function () { tip.hidden = true; });
    });
    if (svg) svg.addEventListener("mouseleave", function () { tip.hidden = true; });
  });
})();

/* Open a collapsed season when a link or the address points at it */
(function () {
  var openHash = function () {
    var id = decodeURIComponent(location.hash.slice(1));
    var el = id && document.getElementById(id);
    if (el && el.tagName === "DETAILS") { el.open = true; el.scrollIntoView(); }
  };
  window.addEventListener("hashchange", openHash);
  if (location.hash) openHash();
})();
