"""Second-generation pages: new home page, roster and wrestler profiles, results,
news, photos, videos, timeline, Our Story, Our Home, Become a Konkrete Kid,
Family, Alumni, and Follow. Called from build.py main() with the build module."""
import re
import datetime as dt
import html
import json
import os
import tomllib

e = html.escape
M = None  # the build module, set in build_all()
SCH_OPEN = '<span class="sch">'
W_OPEN = '<span class="w">'
UL_OPEN = '<ul class="honor-list" role="list">'
TL_TAG = '<p class="tl-tag">PIAA team champions</p>'


def load(name):
    return tomllib.load(open(os.path.join(M.DATA, name), "rb"))


def fmt_date(d):
    return d.strftime("%B %-d, %Y")


def short_date(d):
    return d.strftime("%b %-d")


# ------------------------------------------------------------------ shared pieces
def news_card(R, p, big=False):
    return (f'<article class="news-card{" big" if big else ""}"><a href="{R}news/{p["slug"]}/">'
            f'{M.picture(R, p["photo"], "(min-width: 900px) 33vw, 100vw")}'
            f'<div class="nc-body"><time datetime="{p["date"].isoformat()}">{fmt_date(p["date"])}</time>'
            f'<h3>{e(p["title"])}</h3><p>{e(p["summary"])}</p></div></a></article>')


def follow_block(R, heading_id="follow-title", dark=True):
    nl = M.SITE.get("links", {}).get("signup_form", "") or M.SITE.get("newsletter_url", "")
    action = nl or f'mailto:{M.SITE["email"]}?subject=Sign%20me%20up%20for%20Northampton%20Wrestling%20updates&body=Name%3A%0AConnection%20to%20the%20program%20(parent%2C%20alumni%2C%20fan...)%3A'
    cards = "".join(
        f'<a class="follow-card fc-{k}" href="{M.SITE["social"][k]}" rel="noopener">{M.icon(k)}<span><b>{label}</b>{sub}</span></a>'
        for k, label, sub in (("instagram", "Instagram", "Photos and results"),
                              ("youtube", "YouTube", "Highlights and season videos"),
                              ("facebook", "Facebook", "News for families and alumni"),
                              ("x", "X", "Team news")))
    return f'''<div class="follow-grid">
  <div class="newsletter">
    <h2 id="{heading_id}">Never miss what’s happening</h2>
    <p class="lede">Sign up for updates about the program: big results, schedules, events, and news from the varsity, junior high, and youth teams. We only send something when there’s something worth sharing.</p>
    <a class="btn" href="{action}"{' rel="noopener" target="_blank"' if nl else ""}>Sign up for updates</a>
    {"" if nl else '<p class="fine">Opens an email to the club with “Sign me up” already filled in. Just hit send.</p>'}
  </div>
  <div class="follow-cards">{cards}</div>
</div>'''


def wrestler_url(R, name):
    return f"{R}wrestlers/{M.slug(name)}/"


def avatar(R, w, sizes="200px"):
    if w.get("photo"):
        return M.picture(R, w["photo"], sizes, "wr-photo")
    return f'<span class="wr-photo no-photo"><img src="{R}assets/img/logo-192.png" alt="" width="96" height="82" loading="lazy"></span>'


# ------------------------------------------------------------------ roster data
def honors_for(name, hn=None):
    """Every honor for a wrestler: hall titles/medals/records plus season finishes and awards."""
    hn = hn or name
    hall = {p['name']: p for p in M.hall_json()}
    honors = list(hall.get(hn, {"honors": []})["honors"]) if hn in hall else []
    # postseason finishes and awards from the season files
    for s in M.SEASONS:
        for row in s.get("postseason", []):
            if row[0] in (name, hn):
                for lvl, v in (("District XI", row[2]), ("Northeast Regional", row[3]), ("PIAA", row[4])):
                    if v and not (lvl == "PIAA" and v != "Qualifier") and not (v == "1st" and lvl != "PIAA"):
                        yr = int("20" + s["id"][-2:])
                        label = f"{lvl} {v.lower() if v in ('Qualifier',) else v}"
                        honors.append([yr, label.replace("PIAA Qualifier", "PIAA state qualifier").replace("Northeast Regional Qualifier", "Northeast Regional qualifier"), (row[1] + " lbs") if row[1] else ""])
        for a, who in s.get("awards", []):
            if name in who or hn in who:
                honors.append([int("20" + s["id"][-2:]), a, ""])
        for team, who in s.get("epc", []):
            if name in who or hn in who:
                honors.append([int("20" + s["id"][-2:]), f"EPC all-star, {team.lower()}", ""])
        for who, place in s.get("jv", []):
            if who in (name, hn) or (name.split()[-1] in who and name.split()[0][:3] in who):
                honors.append([int("20" + s["id"][-2:]), f"JV District {place.lower() if place != 'Champion' else 'champion'}", ""])
    seen = set(); clean = []
    def rank(label):
        for i, key in enumerate(("PIAA Champion", "PIAA", "Northeast Regional", "District XI", "100-Win", "Outstanding", "EPC")):
            if label.startswith(key):
                return i
        return 9 if label.startswith("School record") else 8
    for h in sorted(honors, key=lambda h: (-h[0], rank(h[1]), h[1])):
        k = (h[0], h[1])
        if k not in seen:
            seen.add(k); clean.append(h)
    return clean


def roster_data():
    r = load("roster.toml")
    stats = {s["wrestler"]: s for s in M.STATS}
    hall = {p["name"]: p for p in M.hall_json()}
    out = []
    for w in r["wrestler"]:
        w = dict(w)
        w["stats"] = stats.get(w.get("stats_name", ""))
        hn = w.get("hall_name", w["name"])
        clean = honors_for(w["name"], hn)
        w["honors"] = clean
        out.append(w)
    order = {"Senior": 0, "Junior": 1, "Sophomore": 2, "Freshman": 3}
    out.sort(key=lambda w: (0 if w.get("photo") else 1, -(int(w["stats"]["wins"]) if w["stats"] else -1), order.get(w["class"], 9)))
    return r["season"], out


# ------------------------------------------------------------------ home
def count_up(n, label):
    return f'<p><b class="count" data-to="{n}">{n}</b><span>{label}</span></p>'


def next_meta(n):
    """'Wednesday, December 9 · 7:00 PM · Whitehall High School, Whitehall, PA'"""
    return " · ".join([M.event_long_date(n)] + ([n["time"]] if n.get("time") else []) + ([M.event_where(n)] if M.event_where(n) else []))


def match_strip(R):
    res = load("results.toml")
    events = sorted(res.get("event", []), key=lambda x: x["date"])
    today = dt.date.today()
    upcoming = [x for x in events if x.get("end_date", x["date"]) >= today and not x.get("result")]
    done = [x for x in events if x.get("result")]
    feed = ""
    if upcoming:
        n = upcoming[0]
        # The page is only rebuilt when something changes, so site.js re-picks the next event from this list.
        feed = ' data-next="' + e(json.dumps([{"end": x.get("end_date", x["date"]).isoformat(), "t": M.event_title(x), "m": next_meta(x)} for x in upcoming], ensure_ascii=False)) + '"'
        nxt = (f'<p class="ms-k">Next match</p><h2 class="ms-h" data-next-t>{e(M.event_title(n))}</h2>'
               f'<p class="ms-d" data-next-m>{e(next_meta(n))}</p>')
    else:
        nxt = (f'<p class="ms-k">Next match</p><h2 class="ms-h">{res["season"]} schedule coming soon</h2>'
               '<p class="ms-d">Dates post here as soon as they’re released.</p>')
    if done:
        l = done[-1]
        if l.get("kind") == "tournament":
            head = l["result"] + (" place" if re.fullmatch(r"\d+(st|nd|rd|th)", l["result"]) else "")
            sub = l["opponent"]
        else:
            head = {"W": "Win", "L": "Loss", "T": "Tie"}.get(l["result"], l["result"]) + (", " + l["score"].replace("-", "–") if l.get("score") else "")
            sub = M.event_title(l)
        last = (f'<p class="ms-k">Last result</p><h2 class="ms-h">{e(head)}</h2>'
                f'<p class="ms-d">{e(sub)} · {fmt_date(l["date"])}</p>')
    else:
        l = res["last_result"]
        last = (f'<p class="ms-k">Last result</p><h2 class="ms-h">{e(l["result"])}, {e(l["event"])}</h2>'
                f'<p class="ms-d">{fmt_date(l["date"])} · {e(l["location"])}. {e(l["note"])}</p>')
    return f'''<section class="match-strip" aria-label="Next match and last result">
  <div class="wrap ms-grid">
    <div class="ms-cell"{feed}>{nxt}<p class="ms-links"><a href="{R}schedule/">Full schedule</a></p></div>
    <div class="ms-cell">{last}<p class="ms-links"><a href="{R}results/">All results</a></p></div>
  </div>
</section>'''


def last_season(w):
    """Last season's weight and record in small type: '152 lbs · 41–5 in 2025–26'."""
    bits = ([w["weight"] + " lbs"] if w.get("weight") else []) + ([f'{w["stats"]["wins"]}–{w["stats"]["losses"]}'] if w["stats"] and int(w["stats"]["wins"]) else [])
    return f'<i>{" · ".join(bits)} in 2025–26</i>' if bits else ""


def roster_carousel(R, roster):
    cards = "".join(
        f'<li><a class="wr-card" href="{wrestler_url(R, w["name"])}">{avatar(R, w, "220px")}'
        f'<span class="wr-meta"><b>{e(w["name"])}</b>{e(w["class"])}{last_season(w)}</span></a></li>'
        for w in roster)
    return f'''<div class="carousel" data-carousel>
  <div class="car-ctrl"><button type="button" class="car-btn" data-dir="-1" aria-label="Scroll left">‹</button><button type="button" class="car-btn" data-dir="1" aria-label="Scroll right">›</button></div>
  <ul class="car-track" role="list" tabindex="0" aria-label="Returning wrestlers">{cards}</ul>
</div>'''


def build_home():
    R = ""
    S = M
    s = S.CUR
    wins = {r["wrestler"]: r for r in S.STATS}
    w = wins["Brayden Wenrich"]; b = wins["Gabe Ballard"]; t = wins["Trey Wagner"]
    posts = load("news.toml")["post"]
    season, roster = roster_data()
    champ = lambda pid, name, wt, lines: (
        f'<article class="champ-card">{S.picture(R, pid, "(min-width: 900px) 40vw, 90vw")}'
        f'<div class="champ-body"><p class="champ-tag">PIAA Champion at {wt} pounds</p><h3><a href="{wrestler_url(R, name)}">{name}</a></h3>'
        f'<ul role="list">{"".join(f"<li>{l}</li>" for l in lines)}</ul></div></article>')
    T = S.TOTALS
    recent = S.HALL["state"][::-1]
    inside = [("facilities/", "practice-room", "The Room", "Where every Konkrete Kid is made: the wrestling room and Pete Schneider Gymnasium."),
              ("champions/", "showcase-arms-up", "The Tradition", f"{T['team_titles']} team state titles, {T['state']} individual state titles, and {T['streak'][2]} straight years with a State Medalist."),
              ("story/", "program-family", "The Community", "Generations of families in the same black and orange."),
              ("join/", "youth-champs", "The Next Generation", "Kindergarten through varsity, one program and one path.")]
    inside_html = "".join(
        f'<a class="inside{" wide" if i in (0, 3) else ""}" href="{R}{h}">{S.picture(R, pid, "(min-width: 900px) 60vw, 100vw")}<span><b>{ttl}</b>{txt}</span></a>'
        for i, (h, pid, ttl, txt) in enumerate(inside))
    body = f"""
<section class="hero" aria-labelledby="hero-title">
  {S.picture(R, "hero-circle", "100vw", "hero-img", eager=True)}
  <div class="wrap hero-copy">
    <p class="script" aria-hidden="true">Konkrete Kids</p>
    <h1 id="hero-title">Northampton<br>Wrestling</h1>
    <p class="hero-sub">Established 1945</p>
    <p class="hero-actions"><a class="btn" href="roster/">Meet the team</a><a class="btn ghost" href="schedule/">View schedule</a></p>
  </div>
</section>

{match_strip(R)}

<section class="band" aria-labelledby="news-title">
  <div class="wrap">
    <div class="sec-row"><h2 id="news-title">Latest from Northampton</h2><a class="text-link" href="news/">All news</a></div>
    <div class="news-grid lead">{''.join(news_card(R, p, i == 0) for i, p in enumerate(posts[:5]))}</div>
  </div>
</section>

<section class="band dark champs" aria-labelledby="champs-title">
  <div class="wrap">
    {S.section_head('<span id="champs-title">Reigning State Champions</span>', 'Brayden Wenrich and Gabe Ballard won PIAA titles in Hershey in March 2026. Both are back this season.')}
    <div class="champ-grid">
      {champ("portrait-wenrich-2026", "Brayden Wenrich", "114", [f"{w['wins']}–{w['losses']} as a sophomore", "District XI, Northeast Regional, and PIAA Champion", "Fastest pin of the season: 9 seconds", f"{w['career_wins']}–{w['career_losses']} career record"])}
      {champ("portrait-ballard-2026", "Gabe Ballard", "152", [f"{b['wins']}–{b['losses']} as a junior", "District XI, Northeast Regional, and PIAA Champion", "114 takedowns, 238 season team points", f"{b['career_wins']} career wins, a member of the 100-Win Club"])}
    </div>
  </div>
</section>

<section class="band numbers-band" aria-labelledby="numbers-title">
  <div class="wrap">
    <h2 id="numbers-title" class="visually-hidden">Northampton Wrestling by the numbers</h2>
    <div class="big-numbers">
      {count_up(T['team_titles'], 'PIAA team titles')}
      {count_up(T['state'], 'individual state titles')}
      {count_up(T['medals'], 'State Placewinners')}
      {count_up(T['district'], 'District XI Champions')}
      {count_up(T['hundred'], '100-win wrestlers')}
      {count_up(T['wins'], 'dual meet wins')}
    </div>
    <p class="numbers-note">{T['streak'][2]} straight seasons with a State Medalist, every year since {T['streak'][0]}.</p>
  </div>
</section>

<section class="band concrete" aria-labelledby="wall-title">
  <div class="wrap">
    <div class="sec-row"><h2 id="wall-title">The banner wall</h2><a class="text-link" href="champions/">Hall of Champions</a></div>
    <ol class="pennants" role="list" reversed>{''.join(S.pennant(r['year'], S.norm(r['wrestler']), r['weight'], R=R) for r in recent[:10])}</ol>
  </div>
</section>

<section class="band dark" aria-labelledby="kids-title">
  <div class="wrap">
    <div class="sec-row"><h2 id="kids-title">Meet the Konkrete Kids</h2><a class="text-link" href="roster/">Full roster</a></div>
    <p class="lede">Returning varsity wrestlers for {season}. Tap a wrestler for his record and honors.</p>
    {roster_carousel(R, roster)}
  </div>
</section>

<section class="band" aria-labelledby="inside-title">
  <div class="wrap">
    <h2 id="inside-title">Inside the program</h2>
    <div class="inside-grid">{inside_html}</div>
  </div>
</section>

<section class="band dark" aria-labelledby="follow-title" id="follow">
  <div class="wrap">{follow_block(R)}</div>
</section>

<section class="band quote-band">
  <div class="wrap">
    <blockquote class="arena"><p>“The credit belongs to the man who is actually in the arena, whose face is marred by dust and sweat and blood; who strives valiantly; who errs, who comes short again and again… and who at the worst, if he fails, at least fails while daring greatly.”</p><footer>Theodore Roosevelt</footer></blockquote>
  </div>
</section>
"""
    ld = {
        "@context": "https://schema.org", "@type": "SportsTeam", "name": "Northampton Konkrete Kids Wrestling",
        "sport": "Wrestling", "url": S.SITE["domain"] + "/", "foundingDate": "1945",
        "memberOf": {"@type": "SportsOrganization", "name": S.SITE["owner"]},
        "location": {"@type": "Place", "name": S.SITE["school"], "address": {"@type": "PostalAddress", "streetAddress": S.SITE["address"][0], "addressLocality": "Northampton", "addressRegion": "PA", "postalCode": "18067", "addressCountry": "US"}},
        "logo": S.SITE["domain"] + "/assets/img/logo-400.png", "email": S.SITE["email"], "sameAs": list(S.SITE["social"].values()),
    }
    import json
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script>\n'
    return S.page("index.html", "Home", "Northampton Area High School wrestling, the Konkrete Kids: schedule, results, roster, news, and every champion since 1945.", body, "", head, hero_header=True)


# ------------------------------------------------------------------ roster + profiles
def build_roster():
    R = "../"
    season, roster = roster_data()
    cards = "".join(
        f'<li><a class="wr-card light" href="{wrestler_url(R, w["name"])}">{avatar(R, w, "(min-width: 900px) 22vw, 45vw")}'
        f'<span class="wr-meta"><b>{e(w["name"])}</b>{e(w["class"])}{last_season(w)}</span></a></li>'
        for w in roster)
    body = f"""
{M.page_head(R, "Roster", f"Returning varsity wrestlers for {season}. The full lineup posts after wrestle-offs.", "team-mayhem-tight", "50% 22%", cls="fit-photo")}
<section class="band">
  <div class="wrap">
    <ul class="roster-grid" role="list">{cards}</ul>
    <p class="fine">Class is for the {season} season. Records are from 2025–26. Junior high and youth rosters are not posted online.</p>
  </div>
</section>
"""
    M.page("roster/index.html", "Roster", f"Northampton wrestling {season} returning varsity roster.", body, "roster/", og_image="team-mayhem")
    for w in roster:
        build_profile(w, season)
    return M.SITE["domain"] + "/roster/"


def build_profile(w, season):
    R = "../../"
    st = w["stats"]
    statrow = ""
    if st and int(st["wins"]):  # no row of zeros for wrestlers without a varsity win yet
        cells = [("2025–26 record", f'{st["wins"]}–{st["losses"]}'), ("Career record", f'{st["career_wins"]}–{st["career_losses"]}'),
                 ("Pins", st["falls"]), ("Tech falls", st["tech_falls"]), ("Takedowns", st["takedowns"]), ("Dual team points", st["team_points_duals"])]
        statrow = '<div class="facts-row light pf-stats">' + "".join(f"<p><b>{v}</b>{k}</p>" for k, v in cells) + "</div>"
    honors = "".join(f'<li><b>{h[0]}</b><span>{e(h[1])}{(SCH_OPEN + "for " + e(h[3]) + "</span>") if len(h) > 3 else ""}</span>{(W_OPEN + e(h[2]) + "</span>") if h[2] else ""}</li>' for h in w["honors"])
    body = f"""
<section class="band profile-hero dark">
  <div class="wrap pf-grid">
    <div class="pf-photo">{avatar(R, w, "(min-width: 900px) 30vw, 70vw")}</div>
    <div>
      <p class="kicker"><a href="{R}roster/">Roster</a></p>
      <h1>{e(w["name"])}</h1>
      <p class="pf-meta">{e(w["class"])} · {season}{" · " + w["weight"] + " lbs (2025–26)" if w.get("weight") else ""}</p>
      {statrow}
    </div>
  </div>
</section>
<section class="band">
  <div class="wrap">
    <h2>Honors</h2>
    {(UL_OPEN + honors + "</ul>") if honors else "<p>Honors will appear here as the season goes.</p>"}
    <p class="fine"><a href="{R}champions/?q={e(w["name"].split()[-1])}">Search the Hall of Champions</a>. See something we got wrong? <a href="{M.SITE['links']['share_form']}" rel="noopener" target="_blank">Send a correction</a>. (We read everything but can’t reply individually.)</p>
  </div>
</section>
"""
    M.page(f"wrestlers/{M.slug(w['name'])}/index.html", w["name"], f"{w['name']}, Northampton wrestling: record, career record, and honors.", body, "roster/", og_image=w.get("photo") or "team-mayhem")


# ------------------------------------------------------------------ results
def build_results():
    R = "../"
    res = load("results.toml")
    sched = sorted(res.get("event", []), key=lambda x: x["date"])
    ev = [x for x in sched if x.get("result")]
    if ev:
        rows = "".join(
            f'<tr><td>{short_date(x["date"])}</td><th scope="row">{e(M.event_title(x))}</th><td>{e(x.get("kind", "dual").capitalize())}</td>'
            f'<td class="{"gold" if x.get("result") == "W" else ""}">{e(x.get("result", "") or "—")}</td><td>{e(x.get("score", ""))}</td></tr>' for x in ev)
        table = (f'<div class="table-wrap" tabindex="0"><table class="hall"><caption>{res["season"]} varsity results</caption><thead><tr><th scope="col">Date</th><th scope="col">Opponent</th>'
                 f'<th scope="col">Type</th><th scope="col">Result</th><th scope="col">Score</th></tr></thead><tbody>{rows}</tbody></table></div>')
    else:
        opens = (f'The {res["season"]} season opens {sched[0]["date"]:%B %-d} {"against" if sched[0].get("home") else "at"} {e(sched[0]["opponent"])}'
                 if sched else f'The {res["season"]} season starts this winter')
        table = f'<div class="empty-state"><h2>{opens}</h2><p>Results post here during the season.</p><p class="actions"><a class="btn" href="../schedule/">Schedule</a><a class="btn ghost dark-ink" href="../follow/">Get match updates</a></p></div>'
    s = M.CUR
    body = f"""
{M.page_head(R, "Results", f"Varsity match and tournament results for {res['season']}.")}
<section class="band">
  <div class="wrap">{table}</div>
</section>
<section class="band concrete">
  <div class="wrap split even">
    <div><h2>2025–26 team finishes</h2><ul class="results" role="list"><li><span>Dual meet record</span><b>{s['dual_record']}</b></li>{M.result_rows(s['team_finishes'])}</ul></div>
    <div class="prose"><h2>Earlier seasons</h2><p>Every season back to 1946–47 has its own page on <a href="../seasons/">Past Seasons</a>, and the <a href="../champions/">Hall of Champions</a> goes back to 1948.</p></div>
  </div>
</section>
"""
    return M.page("results/index.html", "Results", "Northampton wrestling match results.", body, "results/")


# ------------------------------------------------------------------ news
def build_news():
    R = "../"
    posts = load("news.toml")["post"]
    body = f"""
{M.page_head(R, "News", "The latest from the varsity, junior high, and youth programs.")}
<section class="band">
  <div class="wrap"><h2 class="visually-hidden">All news</h2><div class="news-grid all">{''.join(news_card(R, p) for p in posts)}</div></div>
</section>
"""
    M.page("news/index.html", "News", "Northampton wrestling news.", body, "news/")
    for i, p in enumerate(posts):
        R2 = "../../"
        more = [q for q in posts if q is not p][:2]
        ab = f"""
<article>
  <header class="page-head has-photo">{M.picture(R2, p["photo"], "100vw", "bg", True, alt="")}
    <div class="wrap"><p class="kicker"><a href="{R2}news/">News</a> · <time datetime="{p['date'].isoformat()}">{fmt_date(p['date'])}</time></p><h1 class="article-title">{e(p['title'])}</h1></div></header>
  <div class="band"><div class="wrap prose article-body">{''.join(f'<p>{e(x)}</p>' for x in p['body'])}</div>{('<div class="wrap prose article-body"><h2 class="sub">' + e(p.get("links_title", "Read more")) + '</h2><ul>' + "".join(f'<li><a href="{e(u)}" rel="noopener" target="_blank">{e(tt)}</a></li>' for tt, u in p["links"]) + '</ul></div>') if p.get("links") else ""}{('<div class="wrap top-gap">' + M.gallery(R2, p["gallery"], "news-" + p["slug"]) + '</div>') if p.get("gallery") else ""}</div>
</article>
<section class="band concrete"><div class="wrap"><h2>More news</h2><div class="news-grid two">{''.join(news_card(R2, q) for q in more)}</div></div></section>
"""
        M.page(f"news/{p['slug']}/index.html", p["title"], p["summary"], ab, "news/", og_image=p["photo"])
    return M.SITE["domain"] + "/news/"


# ------------------------------------------------------------------ photos & videos
def build_photos():
    R = "../"
    sets = [("2025–26", M.CUR["gallery"] + ["team-mayhem", "jh-districts"]),
            ("2024–25", ["team-2025", "bench-final-seconds"]),
            ("2023–24", ["showcase-arms-up", "trey-embrace", "team-2024"]),
            ("2022–23", ["showcase-roar", "coach-embrace"]),
            ("The program", ["program-family", "hero-circle", "youth-champs", "youth-autographs", "youth-mat", "staff-corner"])]
    secs = "".join(f'<section class="band{" concrete" if i % 2 else ""}" aria-labelledby="ph-{i}"><div class="wrap"><h2 id="ph-{i}">{lbl}</h2>{M.gallery(R, ids, "set" + str(i))}</div></section>'
                   for i, (lbl, ids) in enumerate(sets))
    body = f"""
{M.page_head(R, "Photos", "Moments from the mat, the room, and the community. Select a photo to view it full size.")}
<nav class="jump wrap" aria-label="Photo sets">{''.join(f'<a href="#ph-{i}">{lbl}</a>' for i, (lbl, _) in enumerate(sets))}</nav>
{secs}
<section class="band dark"><div class="wrap prose"><h2>Share your photos</h2><p>Have great photos or video from a match, a tournament, or an old season? Share them with a note on who’s in them and when, plus the photographer’s name so we can credit them. We read everything but can’t reply individually.</p><p><a class="btn" href="{M.SITE['links']['share_form']}" rel="noopener" target="_blank">Share photos &amp; video</a></p></div></section>
"""
    return M.page("photos/index.html", "Photos", "Northampton wrestling photo galleries.", body, "photos/", og_image="ballard-raised")


def build_videos():
    R = "../"
    pl = M.SITE["social"]["youtube"].split("list=")[-1]
    body = f"""
{M.page_head(R, "Videos", "Season highlights, big moments, and Konkrete Kids history.")}
<section class="band dark">
  <div class="wrap">
    <div class="video-facade" data-yt="{e(pl)}">
      {M.picture(R, "dark-stance", "(min-width: 1180px) 1100px, 100vw", "vf-img", alt="")}
      <button type="button" class="vf-play"><span aria-hidden="true">▶</span> Play all highlight videos</button>
    </div>
    <p class="fine on-dark">Plays from YouTube. Season highlight videos are produced by Coach Mike Sommer. Photo: {e(M.PHOTOS["dark-stance"].get("credit", ""))}.</p>
    <p class="actions"><a class="btn" href="{M.SITE['social']['youtube']}" rel="noopener">Watch on YouTube</a></p>
  </div>
</section>
"""
    return M.page("videos/index.html", "Videos", "Northampton wrestling videos and season highlights.", body, "videos/", og_image="dark-stance")


# ------------------------------------------------------------------ timeline
def build_timeline():
    R = "../"
    ev = load("timeline.toml")["event"]
    decades = sorted({x["year"] // 10 * 10 for x in ev})
    items = []
    for d in decades:
        evs = [x for x in ev if x["year"] // 10 * 10 == d]
        lis = "".join(
            f'<li class="tl-item{" team" if x.get("team") else ""}{" has-photo" if x.get("photo") else ""}{" tall" if x.get("tall") else ""}"><span class="tl-year">{x["year"]}</span>'
            f'<div class="tl-card">{M.picture(R, x["photo"], "(min-width: 900px) 40vw, 90vw") if x.get("photo") else ""}'
            f'<h3>{e(x["title"])}</h3><p>{e(x["text"])}</p>{TL_TAG if x.get("team") else ""}'
            + (f'<p class="tl-more"><a class="text-link" href="{R}{x["link"][1]}">{e(x["link"][0])}</a></p>' if x.get("link") else "")
            + '</div></li>'
            for x in evs)
        items.append(f'<section class="tl-decade" id="d{d}" aria-labelledby="dh{d}"><h2 id="dh{d}" class="tl-dh">{d}s</h2><ol class="tl-list" role="list">{lis}</ol></section>')
    nav = "".join(f'<a href="#d{d}">{d}s</a>' for d in decades)
    body = f"""
{M.page_head(R, "Timeline", "Eighty-plus years of Konkrete Kids wrestling, from the first season in 1945 to today.")}
<nav class="tl-nav" aria-label="Decades"><div class="wrap">{nav}</div></nav>
<div class="band"><div class="wrap tl">{''.join(items)}</div></div>
<section class="band concrete"><div class="wrap prose"><h2>Help us fill in the history</h2><p>Have photos, video, or stories from earlier decades? Share them here. We’ll credit everything we use. We read everything but can’t reply individually.</p><p><a class="btn" href="{M.SITE['links']['share_form']}" rel="noopener" target="_blank">Share photos &amp; video</a></p></div></section>
"""
    return M.page("timeline/index.html", "Timeline", "The history of Northampton Wrestling, 1945 to today.", body, "timeline/", og_image="showcase-arms-up")


# ------------------------------------------------------------------ story, home, join
def build_story():
    R = "../"
    T = M.TOTALS
    eras = M.eras()
    era_rows = "".join(f'<li><span>{e(x["coach"])}</span><b>{" to ".join(f'<span class="nw">{p}</span>' for p in x["seasons"].replace("to present", "to today").split(" to "))}</b></li>' for x in eras)
    body = f"""
{M.page_head(R, "Our Story", "History, tradition, community.", "program-family-tight", "50% 40%")}
<section class="band">
  <div class="wrap split narrow-right top">
    <div class="prose">
      <h2>Since 1945</h2>
      <p>Northampton Wrestling began in 1945. More than 80 seasons later, the program runs from kindergarten through varsity, and every Konkrete Kid comes through the same room, the same expectations, and the same black and orange.</p>
      <p>Along the way the program has won {T['team_titles']} PIAA team titles, won {T['state']} individual state titles, and earned {T['medals']} state medals, with a State Medalist every year since {T['streak'][0]}. Eight head coaches have led the program, and {T['hundred']} wrestlers have won 100 or more varsity matches.</p>
      <h2>What we believe</h2>
      <p>Our mission is to give young people a supportive, demanding place to grow as wrestlers and as responsible, resilient, respectful members of the community.</p>
      <p class="actions"><a class="btn" href="../timeline/">Explore the timeline</a><a class="btn ghost dark-ink" href="../champions/">Hall of Champions</a></p>
    </div>
    <aside class="note-card"><h3>Eight head coaches</h3><ul class="results eras" role="list">{era_rows}</ul></aside>
  </div>
</section>
<section class="band dark"><div class="wrap"><blockquote class="arena dark-q"><p>“I hope I’ll be seen as a guy who really cared about his athletes, as wanting to get every kid he coached to his next level.”</p><footer>Don Rohn, head coach 1982–2000<span class="q-src"><cite>The Morning Call</cite>, April 5, 2000</span></footer></blockquote></div></section>
"""
    return M.page("story/index.html", "Our Story", "The history and philosophy of Northampton Wrestling since 1945.", body, "story/", og_image="program-family")


def build_facilities():
    R = "../"
    body = f"""
{M.page_head(R, "Our Home", "Pete Schneider Gymnasium and the Northampton wrestling room.", "hero-circle", "50% 100%")}
<section class="band">
  <div class="wrap split">
    <div class="prose">
      <h2>Pete Schneider Gymnasium</h2>
      <p>Home duals are wrestled in Pete Schneider Gymnasium at Northampton Area High School, under the program’s state championship banners. Before every home match, the team lies in a circle on the orange mat with their fists together.</p>
      <p>{M.SITE['school']}<br>{'<br>'.join(M.SITE['address'])}</p>
    </div>
    {M.figure(R, "senior-night", "(min-width: 900px) 45vw, 100vw", "wide-fig")}
  </div>
</section>
<section class="band dark">
  <div class="wrap split">
    {M.figure(R, "practice-room", "(min-width: 900px) 45vw, 100vw", "wide-fig")}
    <div class="prose">
      <h2>The room</h2>
      <p>The wrestling room is where the work happens, with the names of Northampton’s district, regional, and State Champions on the walls.</p>
    </div>
  </div>
</section>
<section class="band"><div class="wrap">{M.figure(R, "program-family", "(min-width: 1180px) 1100px, 100vw", "natural-fig")}</div></section>
"""
    return M.page("facilities/index.html", "Our Home", "Pete Schneider Gymnasium and the Northampton wrestling room.", body, "facilities/", og_image="hero-circle")


def build_join():
    R = "../"
    T = M.TOTALS
    pillars = [("Tradition", f"{T['team_titles']} team state titles, {T['state']} individual state titles, and {T['streak'][2]} straight years with a State Medalist."),
               ("Coaching", "A staff that includes a PIAA State Champion, several State Placewinners, and coaches who have been in the program for more than 20 years."),
               ("Training partners", "You train every day beside State Champions and State Medalists."),
               ("Competition", "The varsity wrestles at the Ironman, King of the Mountain, the Mid-Winter Mayhem, and the Parkland Duals."),
               ("Community", "Families from kindergarten through alumni, all in the same black and orange.")]
    path = [("Youth", "Grades K–6", "Northampton Black, Orange, and Novice teams in the Valley Elementary Wrestling League.", "../youth/"),
            ("Junior high", "Grades 7–8", "The bridge to the varsity room. The 2023–24 team won the District XI title.", "../junior-high/"),
            ("JV", "High school", "Matches, tournaments, and the JV District Tournament.", "../high-school/"),
            ("Varsity", "High school", "District XI, Northeast Regional, and the PIAA Championships in Hershey.", "../high-school/"),
            ("College", "Next level", "Members of the Class of 2026 are headed to wrestle at Elizabethtown College and King’s College.", "../alumni/")]
    body = f"""
{M.page_head(R, "Become a Konkrete Kid", "Why Northampton, our home, the path, and how to start.", "showcase-arms-up", "45% 12%")}
<section class="band">
  <div class="wrap">
    <h2>Why Northampton</h2>
    <div class="pillars">{''.join(f'<div><h3>{a}</h3><p>{b}</p></div>' for a, b in pillars)}</div>
  </div>
</section>
<section class="band dark" id="path" aria-labelledby="path-title">
  <div class="wrap">
    <h2 id="path-title">The path</h2>
    <ol class="path-steps" role="list">{''.join(f'<li><a href="{h}"><span class="ps-n">{i + 1}</span><b>{a}</b><i>{g}</i><span>{c}</span></a></li>' for i, (a, g, c, h) in enumerate(path))}</ol>
    <p class="lede">Brayden Wenrich won a District XI junior high title in 2024. Two years later he was a State Champion.</p>
  </div>
</section>
<section class="band">
  <div class="wrap split">
    {M.figure(R, "practice-room", "(min-width: 900px) 45vw, 100vw", "wide-fig")}
    <div class="prose"><h2>Our home</h2><p>Home matches in Pete Schneider Gymnasium under the state championship banners, and daily practice in the wrestling room.</p><p><a class="text-link" href="../facilities/">See our home</a> · <a class="text-link" href="../coaching-staff/">Meet the coaches</a></p></div>
  </div>
</section>
<section class="band concrete" id="start" aria-labelledby="start-title">
  <div class="wrap">
    <h2 id="start-title">Start wrestling</h2>
    <div class="start-grid">
      <div class="note-card"><h3>Grades K–6</h3><p>Join the youth program. No experience needed.</p><a class="btn" href="{M.SITE['links']['youth_registration']}" rel="noopener" target="_blank">Register for youth wrestling</a></div>
      <div class="note-card"><h3>Grades 7–8</h3><p>Join the junior high team with Coach Craig Israel.</p><a class="btn" href="mailto:{M.SITE['email']}?subject=Junior%20high%20wrestling">Email about junior high</a></div>
      <div class="note-card"><h3>High school</h3><p>New to wrestling or new to Northampton? Talk to Coach Provini.</p><a class="btn" href="mailto:{M.SITE['email']}?subject=High%20school%20wrestling">Contact the coaches</a></div>
    </div>
  </div>
</section>
"""
    return M.page("join/index.html", "Become a Konkrete Kid", "Why wrestle at Northampton: tradition, coaching, training partners, and the path from youth to varsity.", body, "join/", og_image="showcase-arms-up")


# ------------------------------------------------------------------ family, alumni, follow
def build_family():
    R = "../"
    faq = [("When does the season start?", 'The high school season begins in November and runs through the PIAA Championships in March. The full schedule is on our <a href="../schedule/">schedule page</a>.'),
           ("Where can I find the schedule?", 'On our <a href="../schedule/">schedule page</a> and the district athletics calendar, which also lists bus times and changes.'),
           ("Can parents watch youth practice?", "In the youth program, only each team’s coaching staff is in the practice room. Matches and tournaments are open to families and fans."),
           ("What if my child misses practice?", "In-season practice and competition attendance is required. Talk to your child’s coach about any special circumstances ahead of time; they’re handled case by case."),
           ("What does a wrestler need before the season?", "Junior high and high school wrestlers need a PIAA physical on file with the district athletic office, plus the weight assessment the coaches schedule early in the season."),
           ("How do I reach a coach?", f'Email <a href="mailto:{M.SITE["email"]}">{M.SITE["email"]}</a> and we’ll get your message to the right coach.')]
    body = f"""
{M.page_head(R, "Parents", "What parents and families need to know.", "senior-night", "50% 40%")}
<section class="band tight"><div class="wrap"><div class="pt-card"><div><p class="ym-label">New to youth wrestling? Start here.</p><h2>How to be a Konkrete Kids parent</h2><p>Ten simple things that matter most, on one page.</p></div><p class="actions"><a class="btn" href="../youth/#pt-title">Read the parent guide</a><a class="btn ghost dark-ink" href="../youth/parent-guide/" target="_blank" rel="noopener">Printable one-pager</a></p></div></div></section>
<section class="band">
  <div class="wrap split even">
    <div class="prose">
      <h2>Season at a glance</h2>
      <ul class="results" role="list"><li><span>High school season</span><b>November – March</b></li><li><span>Postseason</span><b>District XI, Regional, PIAA</b></li><li><span>Home matches</span><b>Pete Schneider Gymnasium</b></li><li><span>Banquet</span><b>Spring</b></li></ul>
      <p class="actions"><a class="btn" href="../schedule/">Schedule</a><a class="btn ghost dark-ink" href="{M.SITE['links']['district_calendar']}" rel="noopener">District calendar</a></p>
    </div>
    <div class="prose">
      <h2>Program expectations</h2>
      <p>Wrestlers are expected to be at every in-season practice and competition, and to represent Northampton with integrity on and off the mat.</p>
      <p>In the youth program, only each team’s coaching staff is in the practice room, and in-season attendance is required: club practices and outside tournaments don’t replace team practice. Special circumstances are handled case by case.</p>
    </div>
  </div>
</section>
<section class="band concrete" id="faq" aria-labelledby="faq-title">
  <div class="wrap"><h2 id="faq-title">FAQs</h2><div class="faq">{''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faq)}</div></div>
</section>
<section class="band dark" id="booster" aria-labelledby="booster-title">
  <div class="wrap">
    <div class="prose">
      <h2 id="booster-title">Booster club</h2>
      <p>The {M.SITE['owner']} supports the program from youth to varsity: the awards banquet, the Charlie Lerch Memorial and Brandon M. Sommer Memorial scholarships, team gear, and more. Volunteers keep it all running.</p>
      <p><a class="btn" href="mailto:{M.SITE['email']}?subject=Volunteer">Volunteer with the club</a></p>
    </div>
  </div>
</section>
"""
    return M.page("family/index.html", "Parents", "Information for Northampton wrestling parents and families: schedule, expectations, FAQs, and the booster club.", body, "family/", og_image="senior-night")


def build_alumni():
    R = "../"
    home = [("Mike Sommer", "Class of 1997 · varsity assistant"), ("Marcus Newsom", "Northampton alumnus · varsity assistant"),
            ("John Paukovits", "3x District XI Champion · varsity assistant"), ("Ethan Szerencsits", "Class of 2020 · varsity assistant"),
            ("Braden Turner", "2008 District and Regional Champion · junior high assistant"), ("Justin Haupt", "1998 and 1999 District XI Champion · junior high assistant")]
    body = f"""
{M.page_head(R, "Alumni", "Once a Konkrete Kid, always a Konkrete Kid.", "banner-wall-names", "30% 45%")}
<section class="band">
  <div class="wrap split even">
    <div class="prose">
      <h2>Where are they now?</h2>
      <p>We want to hear from every Konkrete Kid, from the 1940s to last spring. Where did wrestling take you? Did you wrestle in college, coach, serve, start a family of future Konkrete Kids?</p>
      <p>Send a few lines and a photo, then and now if you have them. We read everything but can’t reply individually.</p>
      <p><a class="btn" href="{M.SITE['links']['share_form']}" rel="noopener" target="_blank">Share your story</a></p>
    </div>
    <div>
      <h2>Konkrete Kids who came home</h2>
      <ul class="results" role="list">{''.join(f'<li><span>{a}</span><b>{b}</b></li>' for a, b in home)}</ul>
    </div>
  </div>
</section>
<section class="band concrete" id="update" aria-labelledby="update-title">
  <div class="wrap prose"><h2 id="update-title">Update your information</h2><p>Get invited to alumni events and program updates. Email your name, graduation year, and best contact info.</p><p><a class="btn" href="mailto:{M.SITE['email']}?subject=Alumni%20update&body=Name%3A%0AGraduation%20year%3A%0AEmail%3A%0APhone%20(optional)%3A">Update your info</a></p></div>
</section>
<section class="band dark" id="support" aria-labelledby="support-title">
  <div class="wrap prose"><h2 id="support-title">Support the program</h2><p>The {M.SITE['owner']} funds scholarships, gear, and the banquet. To donate, sponsor, or help organize an alumni night, email <a href="mailto:{M.SITE['email']}">{M.SITE['email']}</a>.</p></div>
</section>
"""
    return M.page("alumni/index.html", "Alumni", "Northampton wrestling alumni: share your story, update your information, and support the program.", body, "alumni/", og_image="banner-wall-names")


def build_follow():
    R = "../"
    body = f"""
{M.page_head(R, "Follow Northampton", "Program updates by email, and every Konkrete Kids channel in one place.")}
<section class="band dark"><div class="wrap">{follow_block(R, "nl-title")}</div></section>
"""
    return M.page("follow/index.html", "Follow", "Follow Northampton Wrestling: sign up for program updates and find the team on social media.", body, "follow/")


# ------------------------------------------------------------------ State Champion pages
def yt_id(url):
    import re
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def build_champion_pages():
    R = "../../"
    display = {v: k for k, v in M.ALIASES.items()}
    by = {}
    for r in M.HALL["state"]:
        by.setdefault(M.norm(r["wrestler"]), []).append(r)
    order = sorted(by, key=lambda n: -max(int(r["year"]) for r in by[n]))
    for i, name in enumerate(order):
        titles = sorted(by[name], key=lambda r: int(r["year"]))
        c = M.CHAMPS.get(name, {})
        finals = {str(f[0]): f for f in c.get("finals", [])}
        hon = honors_for(display.get(name, name), name)
        tcards = []
        for r in titles:
            f = finals.get(r["year"])
            det = (f'<p class="final">Final: {e(f[3])}{(" over " + e(f[1])) if f[1] else ""}{(", " + e(f[2])) if f[2] else ""}</p>') if f else ""
            tcards.append(f'<li><span class="ty">{r["year"]}</span><span class="tw">{e(r["weight"])}</span><span class="tt">{"PIAA Class AAA Champion" if int(r["year"]) >= 1974 else "PIAA State Champion"}</span>{det}</li>')
        n = len(titles)
        headline = f"{n}x PIAA State Champion" if n > 1 else "PIAA State Champion"
        hero = c.get("hero")
        if hero:
            head = (f'<header class="page-head has-photo champ-head">{M.picture(R, hero, "100vw", "bg", True, alt="")}'
                    f'<div class="wrap"><p class="kicker"><a href="{R}champions/">Hall of Champions</a></p><h1>{e(name)}</h1><p class="lede">{headline} · {", ".join(r["year"] for r in titles)}</p></div></header>')
        else:
            head = (f'<header class="page-head concrete champ-head"><div class="wrap"><p class="kicker"><a href="{R}champions/">Hall of Champions</a></p>'
                    f'<h1>{e(name)}</h1><p class="lede">{headline} · {", ".join(r["year"] for r in titles)}</p></div></header>')
        face = M.picture(R, c["portrait"], "(min-width: 900px) 300px, 70vw", "cp-face", alt=f"{display.get(name, name)} wearing his state championship medals") if c.get("portrait") else ""
        story = "".join("<p>" + re.sub(r"(\d+[\u2013-]\d+(?:[\u2013-]\d+)?)", r'<span class="nw">\1</span>', e(p)) + "</p>" for p in c.get("story", []))
        if not story:
            story = (f'<p>{e(name)} is one of {M.TOTALS["state"]} Konkrete Kids to win a PIAA state title. His full record is below.</p>'
                     f'<p class="ask">Photos, the story of this title, and the state final are coming. Have something to share? '
                     f'<a href="{M.SITE["links"]["share_form"]}" rel="noopener" target="_blank">Share photos, video, or a story</a>. We read everything but can’t reply individually.</p>')
        # video entries: a YouTube URL, or {url, start, end} with times like "15:30" to play just one match
        def secs(x):
            if not x: return 0
            n = 0
            for part in str(x).split(":"): n = n * 60 + int(part)
            return n
        vids = []
        links = []  # non-YouTube videos (e.g. FloWrestling) get a link card instead of an embed
        for item in c.get("video", []):
            u = item if isinstance(item, str) else item.get("url", "")
            if u and not yt_id(u):
                links.append((u, "" if isinstance(item, str) else str(item.get("year", "")), "" if isinstance(item, str) else item.get("site", "")))
            if yt_id(u):
                vids.append((yt_id(u), 0 if isinstance(item, str) else secs(item.get("start")), 0 if isinstance(item, str) else secs(item.get("end")), "" if isinstance(item, str) else str(item.get("year", ""))))
        video = "".join(
            f'<div class="video-facade single" data-ytv="{v}"{f' data-start="{s0}"' if s0 else ""}{f' data-end="{s1}"' if s1 else ""}><img class="vf-img" src="https://i.ytimg.com/vi/{v}/hqdefault.jpg" alt="" loading="lazy"><button type="button" class="vf-play"><span aria-hidden="true">▶</span> Watch the {(yr + " ") if yr else ""}state final</button></div>'
            for v, s0, s1, yr in vids)
        for u, yr, site in links:
            site = site or ("FloWrestling" if "flowrestling" in u else "the web")
            note = '<p class="vl-note">FloWrestling subscription required to watch</p>' if "flowrestling" in u else ""
            video += f'<div class="vl-wrap"><a class="video-link" href="{e(u)}" rel="noopener" target="_blank"><span class="vl-play" aria-hidden="true">▶</span><span><b>Watch the {(yr + " ") if yr else ""}state final on {e(site)}</b><small>Opens in a new tab</small></span></a>{note}</div>'
        if not video and max(int(r["year"]) for r in titles) >= 1980:  # no point asking for 1950s film
            video = f'<div class="empty-state small"><h3>State final video</h3><p>Have video of this final? <a href="{M.SITE["links"]["share_form"]}" rel="noopener" target="_blank">Share a YouTube link</a>. We read everything but can’t reply individually.</p></div>'
        gal = M.gallery(R, c["gallery"], "champ") if c.get("gallery") else ""
        final_band = (f'<section class="band dark"><div class="wrap"><h2>The state final{"s" if len(vids) + len(links) > 1 else ""}</h2>'
                      f'<div class="vid-stack">{video}</div></div></section>') if video else ""
        # featured photo: one moment shown large on its own, with its caption
        fid = c.get("feature")
        feat = (f'<section class="moment" aria-label="Photo"><div class="wrap moment-split">'
                f'<figure class="moment-photo">{M.picture(R, fid, "(min-width: 760px) 440px, 90vw")}</figure>'
                f'<div class="moment-text"><p class="moment-cap">{e(c.get("feature_line", "The moment it all paid off."))}</p>'
                f'<p class="moment-sub">{e(M.PHOTOS[fid].get("caption", ""))}</p></div></div></section>') if fid else ""
        honors = "".join(f'<li><b>{h[0]}</b><span>{e(h[1])}{(SCH_OPEN + "for " + e(h[3]) + "</span>") if len(h) > 3 else ""}</span>{(W_OPEN + e(h[2]) + "</span>") if h[2] else ""}</li>' for h in hon)
        prev = order[i - 1] if i > 0 else None
        nxt = order[i + 1] if i + 1 < len(order) else None
        pn = ('<nav class="champ-nav wrap" aria-label="More champions">'
              + (f'<a href="{R}champions/{M.slug(prev)}/">‹ {e(prev)}</a>' if prev else "<span></span>")
              + f'<a href="{R}champions/#wall-title">All champions</a>'
              + (f'<a href="{R}champions/{M.slug(nxt)}/">{e(nxt)} ›</a>' if nxt else "<span></span>") + "</nav>")
        body = f"""
{head}
<section class="band">
  <div class="wrap cp-grid">
    <aside class="cp-side">{face}<ol class="title-cards" role="list">{''.join(tcards)}</ol></aside>
    <div class="prose cp-story"><h2>The story</h2>{story}</div>
  </div>
</section>
{feat}{final_band}
{f'<section class="band"><div class="wrap"><h2>Photos</h2>{gal}</div></section>' if gal else ''}
<section class="band concrete">
  <div class="wrap">
    <h2>Career at Northampton</h2>
    {(UL_OPEN + honors + "</ul>") if honors else ""}
    <p class="fine">See something we got wrong? <a href="{M.SITE['links']['share_form']}" rel="noopener" target="_blank">Send a correction</a>. (We read everything but can’t reply individually.)</p>
  </div>
</section>
{pn}
"""
        M.page(f"champions/{M.slug(name)}/index.html", f"{name}, State Champion", f"{name}, {headline} for Northampton ({', '.join(r['year'] for r in titles)}).", body, "champions/", og_image=hero or "showcase-arms-up")
    return [M.SITE["domain"] + f"/champions/{M.slug(n)}/" for n in order]


def team_year(season):
    """'1992–93' -> 1993"""
    return int(season[:4]) + 1


def build_team_title_pages():
    """One page per PIAA team-title season: champions/team/<year>/."""
    R = "../../../"
    seasons = load_hall_toml("team-seasons.toml")
    years = [team_year(r["season"]) for r in M.TEAM_TITLES]
    champ_names = {M.norm(r["wrestler"]) for r in M.HALL["state"]}
    def who(n):
        n = M.norm(n)
        return f'<a href="{R}champions/{M.slug(n)}/">{e(n)}</a>' if n in champ_names else e(n)
    def wt(w):
        return int("".join(ch for ch in w if ch.isdigit()) or 0)
    urls = []
    for i, (row, y) in enumerate(zip(M.TEAM_TITLES, years)):
        s = seasons.get(str(y), {})
        ys = str(y)
        champs = sorted([r for r in M.HALL["state"] if r["year"] == ys], key=lambda r: wt(r["weight"]))
        medals = sorted([r for r in M.HALL["medals"] if r["year"] == ys], key=lambda r: (int(r["place"]), wt(r["weight"])))
        dist = sorted([r for r in M.HALL["district"] if r["year"] == ys], key=lambda r: wt(r["weight"]))
        reg = sorted([r for r in M.HALL["regional"] if r["year"] == ys], key=lambda r: wt(r["weight"]))
        podium = [(1, r) for r in champs] + [(int(r["place"]), r) for r in medals]
        place_label = lambda p: "Champion" if p == 1 else f"{p}{M.ordinal_suffix(p)}"
        pod = "".join(f'<li class="pl-{min(p, 4)}"><span class="pp">{place_label(p)}</span><span class="pn">{who(r["wrestler"])}</span><span class="pw">{e(r["weight"])}</span></li>' for p, r in podium)
        stats = [(s.get("record", ""), "dual record"), (str(len(champs)), "State Champion" + ("s" if len(champs) != 1 else "")),
                 (str(len(podium)), "State Place Winners"), (str(len(dist)), "District XI Champions"), (str(len(reg)), "Regional Champions")]
        stat_html = "".join(f'<li><b>{e(v)}</b><span>{e(l)}</span></li>' for v, l in stats if v)
        story = "".join("<p>" + re.sub(r"(\d+(?:\.\d+)?[–-]\d+(?:\.\d+)?)", r'<span class="nw">\1</span>', e(x)) + "</p>" for x in s.get("story", []))
        if not story:
            story = f'<p>Northampton won the PIAA Class AAA team title in {e(row["season"])}. The full story of this season is coming.</p>'
        post = "".join(f'<li><span class="ps">{e(a)}</span><span class="pr">{e(b)}</span></li>' for a, b in s.get("postseason", []))
        hl = "".join(f'<li><span class="hd">{e(a)}</span><span>{e(b)}</span></li>' for a, b in s.get("highlights", []))
        lst = lambda rows: "".join(f'<li>{who(r["wrestler"])} <span class="w">{e(r["weight"])}</span></li>' for r in rows)
        prev = years[i - 1] if i > 0 else None
        nxt = years[i + 1] if i + 1 < len(years) else None
        nav = ('<nav class="champ-nav wrap" aria-label="More team titles">'
               + (f'<a href="{R}champions/team/{prev}/">‹ {prev}</a>' if prev else "<span></span>")
               + f'<a href="{R}champions/#team-title">All team titles</a>'
               + (f'<a href="{R}champions/team/{nxt}/">{nxt} ›</a>' if nxt else "<span></span>") + "</nav>")
        sid = f"{y - 1}-{str(y)[2:]}"
        v = M.season_videos(sid, row["season"])
        n_v = len(M.SEASON_VIDEOS.get(sid, []))
        vids = (f'<h2>Season highlight video{"s" if n_v > 1 else ""}</h2>' + v) if v else ""
        coach = s.get("coach", "")
        lede = f'PIAA Class AAA team champions · {e(row["season"])}' + (f' · Coach {e(coach)}' if coach else "")
        body = f"""
<header class="page-head concrete champ-head team-head"><div class="wrap"><p class="kicker"><a href="{R}champions/">Hall of Champions</a></p>
<h1>{y} State Champions</h1><p class="lede">{lede}</p>
<p class="tt-count">Team title {i + 1} of {len(years)}</p></div></header>
<section class="band tight"><div class="wrap"><ul class="ts-stats" role="list">{stat_html}</ul></div></section>
<section class="band">
  <div class="wrap cp-grid">
    <aside class="cp-side">
      {f'<h2 class="side-h">Postseason</h2><ol class="post-list" role="list">{post}</ol>' if post else ''}
      {f'<p class="side-note">{e(s["league"])}</p>' if s.get("league") else ''}
    </aside>
    <div class="prose cp-story"><h2>The season</h2>{story}<p><a class="text-link" href="{R}seasons/{sid}/">Results, duals, and video for {e(row["season"])} ›</a></p></div>
  </div>
</section>
{f'<section class="band tight" id="video"><div class="wrap">{vids}</div></section>' if vids else ''}
<section class="band dark">
  <div class="wrap">
    <h2>On the podium at Hershey</h2>
    <ol class="tt-podium" role="list">{pod}</ol>
  </div>
</section>
<section class="band concrete">
  <div class="wrap split even">
    <div>{f'<h2>Season highlights</h2><ol class="hl-list" role="list">{hl}</ol>' if hl else ''}</div>
    <div>
      {f'<h2>District XI Champions</h2><ul class="mini-list" role="list">{lst(dist)}</ul>' if dist else ''}
      {f'<h2>Northeast Regional Champions</h2><ul class="mini-list" role="list">{lst(reg)}</ul>' if reg else ''}
    </div>
  </div>
</section>
{nav}
"""
        M.page(f"champions/team/{y}/index.html", f"{y} PIAA team champions", f"Northampton's {row['season']} PIAA Class AAA team championship season: record, story, State Place Winners, and postseason.", body, "champions/")
        urls.append(M.SITE["domain"] + f"/champions/team/{y}/")
    return urls


def load_hall_toml(name):
    with open(os.path.join(M.ROOT, "data", "hall", name), "rb") as f:
        return tomllib.load(f)


def build_all(module):
    global M
    M = module
    urls = [build_roster(), build_results(), build_news(), build_videos(), build_timeline(),
            build_story(), build_facilities(), build_join(), build_family(), build_alumni(), build_follow()]
    urls += build_champion_pages()
    urls += build_team_title_pages()
    return urls
