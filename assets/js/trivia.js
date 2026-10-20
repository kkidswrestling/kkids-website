/* Konkrete Kids trivia: rounds as tabs, tap an answer, see the fact, score at the end. Nothing is stored. */
(function () {
  "use strict";
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tv-tab"));
  var rounds = Array.prototype.slice.call(document.querySelectorAll(".tv-round"));
  if (!tabs.length) return;

  var show = function (i, focus) {
    tabs.forEach(function (t, k) { t.setAttribute("aria-selected", String(k === i)); t.tabIndex = k === i ? 0 : -1; });
    rounds.forEach(function (r, k) { r.hidden = k !== i; });
    if (focus) tabs[i].focus();
  };
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { show(i); });
    t.addEventListener("keydown", function (e) {
      var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) { e.preventDefault(); show((i + d + tabs.length) % tabs.length, true); }
    });
  });

  var cheers = ["Nice!", "You got it.", "That's right.", "Konkrete Kid knowledge.", "Correct!"];
  var finish = function (round) {
    var qs = round.querySelectorAll(".tv-q"), right = round.querySelectorAll(".tv-q.is-right").length;
    var box = round.querySelector(".tv-score");
    var title = tabs[rounds.indexOf(round)].firstChild.textContent;
    var pct = right / qs.length;
    box.querySelector(".tv-score-big").textContent = right + " / " + qs.length;
    box.querySelector(".tv-score-line").textContent = pct === 1 ? "Perfect round. You belong on the banner wall." :
      pct >= 0.7 ? "Strong round. You know your Konkrete Kids." :
      pct >= 0.4 ? "Not bad. A few more trips through the Hall of Champions and you'll have it." :
      "Every champion started somewhere. Try it again.";
    box.dataset.share = "I got " + right + "/" + qs.length + " in the " + title + " round of Konkrete Kids trivia. Can you beat it?";
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  rounds.forEach(function (round) {
    round.addEventListener("click", function (e) {
      var b = e.target.closest(".tv-choice");
      if (b) {
        var q = b.closest(".tv-q");
        if (q.classList.contains("is-done")) return;
        var ans = q.dataset.answer, ok = b.dataset.i === ans;
        q.classList.add("is-done", ok ? "is-right" : "is-wrong");
        q.querySelectorAll(".tv-choice").forEach(function (c) {
          c.disabled = true;
          if (c.dataset.i === ans) c.classList.add("right");
          else if (c === b) c.classList.add("wrong");
        });
        var correct = q.querySelector('.tv-choice[data-i="' + ans + '"]').textContent;
        q.querySelector(".tv-verdict").textContent = ok ? cheers[Math.floor(Math.random() * cheers.length)] : "Not quite. It's " + correct + ".";
        q.querySelector(".tv-reveal").hidden = false;
        if (round.querySelectorAll(".tv-q:not(.is-done)").length === 0) finish(round);
        return;
      }
      if (e.target.closest(".tv-again")) {
        round.querySelectorAll(".tv-q").forEach(function (q) {
          q.classList.remove("is-done", "is-right", "is-wrong");
          q.querySelector(".tv-reveal").hidden = true;
          q.querySelectorAll(".tv-choice").forEach(function (c) { c.disabled = false; c.classList.remove("right", "wrong"); });
        });
        round.querySelector(".tv-score").hidden = true;
        round.querySelector(".tv-copied").hidden = true;
        round.scrollIntoView({ behavior: "smooth" });
        return;
      }
      var nx = e.target.closest(".tv-next");
      if (nx) { show(+nx.dataset.next); document.querySelector(".tv-tabs").scrollIntoView({ behavior: "smooth" }); return; }
      if (e.target.closest(".tv-share")) {
        var box = round.querySelector(".tv-score"), text = box.dataset.share, url = location.href.split("#")[0];
        if (navigator.share) { navigator.share({ title: "Konkrete Kids Trivia", text: text, url: url }).catch(function () {}); return; }
        var done = function () { round.querySelector(".tv-copied").hidden = false; };
        try { navigator.clipboard.writeText(text + " " + url).then(done, function () { window.prompt("Copy this:", text + " " + url); }); }
        catch (err) { window.prompt("Copy this:", text + " " + url); }
      }
    });
  });
})();
