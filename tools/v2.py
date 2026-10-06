"""Second-generation pages: new home page, roster and wrestler profiles, results,
news, photos, videos, timeline, Our Story, Our Home, Become a Konkrete Kid,
Family, Alumni, and Follow. Called from build.py main() with the build module."""
import datetime as dt
import html
import os
import tomllib

e = html.escape
M = None  # the build module, set in build_all()
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
    nl = M.SITE.get("newsletter_url", "")
    action = nl or f'mailto:{M.SITE["email"]}?subject=Subscribe%20me%20to%20Coach%E2%80%99s%20Corner&body=Please%20add%20this%20email%20to%20the%20Northampton%20Wrestling%20newsletter.'
    cards = "".join(
        f'<a class="follow-card fc-{k}" href="{M.SITE["social"][k]}" rel="noopener">{M.icon(k)}<span><b>{label}</b>{sub}</span></a>'
        for k, label, sub in (("instagram", "Instagram", "Match-day photos and results"),
                              ("youtube", "YouTube", "Highlights and season videos"),
                              ("facebook", "Facebook", "News for families and alumni"),
                              ("x", "X", "Live updates")))
    return f'''<div class="follow-grid">
  <div class="newsletter">
    <h2 id="{heading_id}">Never miss what’s happening</h2>
    <p class="lede">Coach’s Corner is a note from Coach Provini, weekly in season and monthly in the off-season: the varsity, junior high, and youth programs, the week’s schedule, a wrestler spotlight, and a moment from the archives.</p>
    <a class="btn" href="{action}">{"Sign up for Coach’s Corner" if nl else "Email us to sign up"}</a>
    {"" if nl else '<p class="fine">Opens an email to the club. Online sign-up is coming soon.</p>'}
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
def roster_data():
    r = load("roster.toml")
    stats = {s["wrestler"]: s for s in M.STATS}
    hall = {p["name"]: p for p in M.hall_json()}
    out = []
    for w in r["wrestler"]:
        w = dict(w)
        w["stats"] = stats.get(w.get("stats_name", ""))
        hn = w.get("hall_name", w["name"])
        honors = list(hall.get(hn, {"honors": []})["honors"]) if hn in hall else []
        # postseason finishes and awards from the season files
        for s in M.SEASONS:
            for row in s.get("postseason", []):
                if row[0] in (w["name"], hn):
                    for lvl, v in (("District XI", row[2]), ("Northeast Regional", row[3]), ("PIAA", row[4])):
                        if v and not (lvl == "PIAA" and v != "Qualifier") and not (v == "1st" and lvl != "PIAA"):
                            yr = int("20" + s["id"][-2:])
                            label = f"{lvl} {v.lower() if v in ('Qualifier',) else v}"
                            honors.append([yr, label.replace("PIAA Qualifier", "PIAA state qualifier").replace("Northeast Regional Qualifier", "Northeast Regional qualifier"), (row[1] + " lbs") if row[1] else ""])
            for a, who in s.get("awards", []):
                if w["name"] in who or hn in who:
                    honors.append([int("20" + s["id"][-2:]), a, ""])
            for team, who in s.get("epc", []):
                if w["name"] in who or hn in who:
                    honors.append([int("20" + s["id"][-2:]), f"EPC all-star, {team.lower()}", ""])
            for who, place in s.get("jv", []):
                if who in (w["name"], hn) or (w["name"].split()[-1] in who and w["name"].split()[0][:3] in who):
                    honors.append([int("20" + s["id"][-2:]), f"JV District {place.lower() if place != 'Champion' else 'champion'}", ""])
        seen = set(); clean = []
        def rank(label):
            for i, key in enumerate(("PIAA champion", "PIAA", "Northeast Regional", "District XI", "100-Win", "Outstanding", "EPC")):
                if label.startswith(key):
                    return i
            return 9 if label.startswith("School record") else 8
        for h in sorted(honors, key=lambda h: (-h[0], rank(h[1]), h[1])):
            k = (h[0], h[1])
            if k not in seen:
                seen.add(k); clean.append(h)
        w["honors"] = clean
        out.append(w)
    order = {"Senior": 0, "Junior": 1, "Sophomore": 2, "Freshman": 3}
    out.sort(key=lambda w: (0 if w.get("photo") else 1, -(int(w["stats"]["wins"]) if w["stats"] else -1), order.get(w["class"], 9)))
    return r["season"], out


# ------------------------------------------------------------------ home
def count_up(n, label):
    return f'<p><b class="count" data-to="{n}">{n}</b><span>{label}</span></p>'


def match_strip(R):
    res = load("results.toml")
    events = res.get("event", [])
    today = dt.date.today()
    upcoming = sorted([x for x in events if x["date"] >= today and not x.get("result")], key=lambda x: x["date"])
    done = sorted([x for x in events if x.get("result")], key=lambda x: x["date"])
    if upcoming:
        n = upcoming[0]
        nxt = (f'<p class="ms-k">Next match</p><h2 class="ms-h">{"vs." if n.get("home") else "at"} {e(n["opponent"])}</h2>'
               f'<p class="ms-d">{fmt_date(n["date"])}{" · " + e(n["time"]) if n.get("time") else ""} · {e(n.get("location", ""))}</p>')
    else:
        nxt = ('<p class="ms-k">Next match</p><h2 class="ms-h">2026–27 schedule coming soon</h2>'
               '<p class="ms-d">The season opens this winter. Dates post here as soon as they’re released.</p>')
    if done:
        l = done[-1]
        last = (f'<p class="ms-k">Last result</p><h2 class="ms-h">{e(l["result"])} {e(l.get("score", ""))}</h2>'
                f'<p class="ms-d">{"vs." if l.get("home") else "at"} {e(l["opponent"])} · {fmt_date(l["date"])}</p>')
    else:
        l = res["last_result"]
        last = (f'<p class="ms-k">Last result</p><h2 class="ms-h">{e(l["result"])}, {e(l["event"])}</h2>'
                f'<p class="ms-d">{fmt_date(l["date"])} · {e(l["location"])}. {e(l["note"])}</p>')
    return f'''<section class="match-strip" aria-label="Next match and last result">
  <div class="wrap ms-grid">
    <div class="ms-cell">{nxt}<p class="ms-links"><a href="{R}schedule/">Full schedule</a></p></div>
    <div class="ms-cell">{last}<p class="ms-links"><a href="{R}results/">All results</a></p></div>
  </div>
</section>'''


def roster_carousel(R, roster):
    cards = "".join(
        f'<li><a class="wr-card" href="{wrestler_url(R, w["name"])}">{avatar(R, w, "220px")}'
        f'<span class="wr-meta"><b>{e(w["name"])}</b>{e(w["class"])}{" · " + w["weight"] + " lbs" if w.get("weight") else ""}'
        f'{"<i>" + w["stats"]["wins"] + "–" + w["stats"]["losses"] + " in 2025–26</i>" if w["stats"] and int(w["stats"]["wins"]) else ""}</span></a></li>'
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
        f'<div class="champ-body"><p class="champ-tag">PIAA champion at {wt} pounds</p><h3><a href="{wrestler_url(R, name)}">{name}</a></h3>'
        f'<ul role="list">{"".join(f"<li>{l}</li>" for l in lines)}</ul></div></article>')
    T = S.TOTALS
    recent = S.HALL["state"][::-1]
    inside = [("facilities/", "practice-room", "The Room", "Where every Konkrete Kid is made: the wrestling room and Pete Schneider Gym."),
              ("champions/", "showcase-arms-up", "The Tradition", f"{T['team_titles']} team state titles, {T['state']} state champions, and {T['streak'][2]} straight years with a state medalist."),
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
    <p class="hero-sub">We never sacrifice goodness for greatness.</p>
    <p class="hero-actions"><a class="btn" href="roster/">Meet the team</a><a class="btn ghost" href="schedule/">View schedule</a></p>
  </div>
</section>

{match_strip(R)}

<section class="band" aria-labelledby="news-title">
  <div class="wrap">
    <div class="sec-row"><h2 id="news-title">Latest from Northampton</h2><a class="text-link" href="news/">All news</a></div>
    <div class="news-grid">{''.join(news_card(R, p, i == 0) for i, p in enumerate(posts[:3]))}</div>
  </div>
</section>

<section class="band dark champs" aria-labelledby="champs-title">
  <div class="wrap">
    {S.section_head('<span id="champs-title">Reigning state champions</span>', 'Brayden Wenrich and Gabe Ballard won PIAA titles in Hershey in March 2026. Both are back this season.')}
    <div class="champ-grid">
      {champ("portrait-wenrich-2026", "Brayden Wenrich", "114", [f"{w['wins']}–{w['losses']} as a sophomore", "District XI, Northeast Regional, and PIAA champion", "Fastest pin of the season: 9 seconds", f"{w['career_wins']}–{w['career_losses']} career record"])}
      {champ("portrait-ballard-2026", "Gabe Ballard", "152", [f"{b['wins']}–{b['losses']} as a junior", "District XI, Northeast Regional, and PIAA champion", "114 takedowns, 238 team points", f"{b['career_wins']} career wins, a member of the 100-Win Club"])}
    </div>
  </div>
</section>

<section class="moment" aria-label="Photo">
  <div class="wrap moment-split">
    <figure class="moment-photo">{S.picture(R, "trey-embrace", "(min-width: 760px) 440px, 90vw")}</figure>
    <div class="moment-text">
      <p class="moment-cap">The moment it all pays off.</p>
      <p class="moment-sub">{e(S.PHOTOS["trey-embrace"]["caption"])}</p>
    </div>
  </div>
</section>

<section class="band numbers-band" aria-labelledby="numbers-title">
  <div class="wrap">
    <h2 id="numbers-title" class="visually-hidden">Northampton Wrestling by the numbers</h2>
    <div class="big-numbers">
      {count_up(T['team_titles'], 'PIAA team titles')}
      {count_up(T['state'], 'PIAA state champions')}
      {count_up(T['medals'], 'state medals')}
      {count_up(T['district'], 'District XI titles')}
      {count_up(T['hundred'], '100-win wrestlers')}
      {count_up(T['wins'], 'dual meet wins')}
    </div>
    <p class="numbers-note">{T['streak'][2]} straight seasons with a state medalist, every year since {T['streak'][0]}.</p>
  </div>
</section>

<section class="band concrete" aria-labelledby="wall-title">
  <div class="wrap">
    <div class="sec-row"><h2 id="wall-title">The banner wall</h2><a class="text-link" href="champions/">Hall of Champions</a></div>
    <ol class="pennants" role="list" reversed>{''.join(S.pennant(r['year'], S.norm(r['wrestler']), r['weight']) for r in recent[:10])}</ol>
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
        "location": {"@type": "Place", "name": S.SITE["gym"] + ", " + S.SITE["school"], "address": {"@type": "PostalAddress", "streetAddress": S.SITE["address"][0], "addressLocality": "Northampton", "addressRegion": "PA", "postalCode": "18067", "addressCountry": "US"}},
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
        f'<span class="wr-meta"><b>{e(w["name"])}</b>{e(w["class"])}{" · " + w["weight"] + " lbs" if w.get("weight") else ""}'
        f'{"<i>" + w["stats"]["wins"] + "–" + w["stats"]["losses"] + " in 2025–26</i>" if w["stats"] and int(w["stats"]["wins"]) else ""}</span></a></li>'
        for w in roster)
    body = f"""
{M.page_head(R, "Roster", f"Returning varsity wrestlers for {season}. The full lineup posts after wrestle-offs.", "team-mayhem", "50% 40%")}
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
    if st:
        cells = [("2025–26 record", f'{st["wins"]}–{st["losses"]}'), ("Career record", f'{st["career_wins"]}–{st["career_losses"]}'),
                 ("Pins", st["falls"]), ("Tech falls", st["tech_falls"]), ("Takedowns", st["takedowns"]), ("Dual team points", st["team_points_duals"])]
        statrow = '<div class="facts-row light pf-stats">' + "".join(f"<p><b>{v}</b>{k}</p>" for k, v in cells) + "</div>"
    honors = "".join(f'<li><b>{h[0]}</b><span>{e(h[1])}</span>{(W_OPEN + e(h[2]) + "</span>") if h[2] else ""}</li>' for h in w["honors"])
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
    <p class="fine">From Northampton banquet programs and season results. <a href="{R}champions/?q={e(w["name"].split()[-1])}">Search the Hall of Champions</a>.</p>
  </div>
</section>
"""
    M.page(f"wrestlers/{M.slug(w['name'])}/index.html", w["name"], f"{w['name']}, Northampton wrestling: record, career record, and honors.", body, "roster/", og_image=w.get("photo") or "team-mayhem")


# ------------------------------------------------------------------ results
def build_results():
    R = "../"
    res = load("results.toml")
    ev = sorted(res.get("event", []), key=lambda x: x["date"])
    if ev:
        rows = "".join(
            f'<tr><td>{short_date(x["date"])}</td><th scope="row">{"vs." if x.get("home") else "at"} {e(x["opponent"])}</th><td>{e(x.get("kind", ""))}</td>'
            f'<td class="{"gold" if x.get("result") == "W" else ""}">{e(x.get("result", "") or "—")}</td><td>{e(x.get("score", ""))}</td></tr>' for x in ev)
        table = (f'<div class="table-wrap"><table class="hall"><caption>{res["season"]} varsity results</caption><thead><tr><th scope="col">Date</th><th scope="col">Opponent</th>'
                 f'<th scope="col">Type</th><th scope="col">Result</th><th scope="col">Score</th></tr></thead><tbody>{rows}</tbody></table></div>')
    else:
        table = '<div class="empty-state"><h2>The 2026–27 season starts this winter</h2><p>Results post here after every match, usually the same night.</p><p class="actions"><a class="btn" href="../schedule/">Schedule</a><a class="btn ghost dark-ink" href="../follow/">Get match updates</a></p></div>'
    s = M.CUR
    body = f"""
{M.page_head(R, "Results", f"Varsity match and tournament results for {res['season']}.")}
<section class="band">
  <div class="wrap">{table}</div>
</section>
<section class="band concrete">
  <div class="wrap split even">
    <div><h2>2025–26 team finishes</h2><ul class="results" role="list"><li><span>Dual meet record</span><b>{s['dual_record']}</b></li>{M.result_rows(s['team_finishes'])}</ul></div>
    <div class="prose"><h2>Earlier seasons</h2><p>Full results, postseason finishes, and awards for every season since 2022–23 are on the <a href="../seasons/">Past Seasons</a> page, and the <a href="../champions/">Hall of Champions</a> goes back to 1948.</p></div>
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
  <div class="band"><div class="wrap prose article-body">{''.join(f'<p>{e(x)}</p>' for x in p['body'])}</div></div>
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
            ("The program", ["program-family", "hero-circle", "youth-champs", "youth-autographs", "youth-mat", "staff-corner", "coaches-embrace"])]
    secs = "".join(f'<section class="band{" concrete" if i % 2 else ""}" aria-labelledby="ph-{i}"><div class="wrap"><h2 id="ph-{i}">{lbl}</h2>{M.gallery(R, ids, "set" + str(i))}</div></section>'
                   for i, (lbl, ids) in enumerate(sets))
    body = f"""
{M.page_head(R, "Photos", "Moments from the mat, the room, and the community. Select a photo to view it full size.")}
<nav class="jump wrap" aria-label="Photo sets">{''.join(f'<a href="#ph-{i}">{lbl}</a>' for i, (lbl, _) in enumerate(sets))}</nav>
{secs}
<section class="band dark"><div class="wrap prose"><h2>Share your photos</h2><p>Have great photos from a match, a tournament, or an old season? Email them to <a href="mailto:{M.SITE['email']}">{M.SITE['email']}</a> with who and when, and the photographer’s name so we can credit them.</p></div></section>
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
      <button type="button" class="vf-play"><span aria-hidden="true">▶</span> Play the Northampton Wrestling playlist</button>
    </div>
    <p class="fine on-dark">Plays from YouTube. Season highlight videos are produced by Coach Mike Sommer.</p>
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
            f'<li class="tl-item{" team" if x.get("team") else ""}{" has-photo" if x.get("photo") else ""}"><span class="tl-year">{x["year"]}</span>'
            f'<div class="tl-card">{M.picture(R, x["photo"], "(min-width: 900px) 40vw, 90vw") if x.get("photo") else ""}'
            f'<h3>{e(x["title"])}</h3><p>{e(x["text"])}</p>{TL_TAG if x.get("team") else ""}</div></li>'
            for x in evs)
        items.append(f'<section class="tl-decade" id="d{d}" aria-labelledby="dh{d}"><h2 id="dh{d}" class="tl-dh">{d}s</h2><ol class="tl-list" role="list">{lis}</ol></section>')
    nav = "".join(f'<a href="#d{d}">{d}s</a>' for d in decades)
    body = f"""
{M.page_head(R, "Timeline", "Eighty-plus years of Konkrete Kids wrestling, from the first season in 1945 to today.")}
<nav class="tl-nav" aria-label="Decades"><div class="wrap">{nav}</div></nav>
<div class="band"><div class="wrap tl">{''.join(items)}</div></div>
<section class="band concrete"><div class="wrap prose"><h2>Help us fill in the history</h2><p>Have photos, newspaper clippings, or stories from earlier decades? Email <a href="mailto:{M.SITE['email']}">{M.SITE['email']}</a>. We’ll credit everything we use.</p></div></section>
"""
    return M.page("timeline/index.html", "Timeline", "The history of Northampton Wrestling, 1945 to today.", body, "timeline/", og_image="showcase-arms-up")


# ------------------------------------------------------------------ story, home, join
def build_story():
    R = "../"
    T = M.TOTALS
    eras = M.eras()
    era_rows = "".join(f'<li><span>{e(x["coach"])}</span><b>{x["seasons"].replace("to present", "to today")}</b></li>' for x in eras)
    body = f"""
{M.page_head(R, "Our Story", "History, tradition, community.", "program-family", "50% 40%")}
<section class="band">
  <div class="wrap split narrow-right top">
    <div class="prose">
      <h2>Since 1945</h2>
      <p>Northampton Wrestling began in 1945. More than 80 seasons later, the program runs from kindergarten through varsity, and every Konkrete Kid comes through the same room, the same expectations, and the same black and orange.</p>
      <p>Along the way the program has won {T['team_titles']} PIAA team titles, crowned {T['state']} individual state champions, and earned {T['medals']} state medals, with a state medalist every year since {T['streak'][0]}. Eight head coaches have led the program, and {T['hundred']} wrestlers have won 100 or more varsity matches.</p>
      <h2>What we believe</h2>
      <p>Our mission is to give young people a supportive, demanding place to grow as wrestlers and as responsible, resilient, respectful members of the community.</p>
      <p><strong>We never sacrifice goodness for greatness.</strong> Integrity and honor come first. Winning is the byproduct.</p>
      <p class="actions"><a class="btn" href="../timeline/">Explore the timeline</a><a class="btn ghost dark-ink" href="../champions/">Hall of Champions</a></p>
    </div>
    <aside class="note-card"><h3>Eight head coaches</h3><ul class="results" role="list">{era_rows}</ul></aside>
  </div>
</section>
<section class="band dark"><div class="wrap"><blockquote class="arena dark-q"><p>“It is not the critic who counts… The credit belongs to the man who is actually in the arena.”</p><footer>Theodore Roosevelt</footer></blockquote></div></section>
"""
    return M.page("story/index.html", "Our Story", "The history and philosophy of Northampton Wrestling since 1945.", body, "story/", og_image="program-family")


def build_facilities():
    R = "../"
    body = f"""
{M.page_head(R, "Our Home", "Pete Schneider Gym and the Northampton wrestling room.", "hero-circle", "50% 100%")}
<section class="band">
  <div class="wrap split">
    <div class="prose">
      <h2>Pete Schneider Gym</h2>
      <p>Home duals are wrestled in Pete Schneider Gym at Northampton Area High School, under the program’s state championship banners. Before every home match, the team lies in a circle on the orange mat with their fists together.</p>
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
      <p>The wrestling room is where the work happens, with the names of Northampton’s District, Regional, and State champions on the walls.</p>
    </div>
  </div>
</section>
<section class="band"><div class="wrap">{M.figure(R, "program-family", "(min-width: 1180px) 1100px, 100vw", "natural-fig")}</div></section>
"""
    return M.page("facilities/index.html", "Our Home", "Pete Schneider Gym and the Northampton wrestling room.", body, "facilities/", og_image="hero-circle")


def build_join():
    R = "../"
    T = M.TOTALS
    pillars = [("Tradition", f"{T['team_titles']} team state titles, {T['state']} state champions, and {T['streak'][2]} straight years with a state medalist."),
               ("Coaching", "A staff that includes a PIAA state champion, several state placewinners, and coaches who have been in the program for more than 20 years."),
               ("Training partners", "You train every day beside state champions and state medalists."),
               ("Competition", "The varsity wrestles at the Ironman, King of the Mountain, the Mid-Winter Mayhem, and the Parkland Duals."),
               ("Community", "Families from kindergarten through alumni, all in the same black and orange.")]
    path = [("Youth", "Grades K–6", "Northampton Black, Orange, and Novice teams in the Valley Elementary Wrestling League.", "../youth/"),
            ("Junior high", "Grades 7–8", "The bridge to the varsity room. The 2023–24 team won the District XI title.", "../junior-high/"),
            ("JV", "High school", "Matches, tournaments, and the JV District Tournament.", "../high-school/"),
            ("Varsity", "High school", "District XI, Northeast Regional, and the PIAA Championships in Hershey.", "../high-school/"),
            ("College", "Next level", "Members of the Class of 2026 are headed to wrestle at Elizabethtown and King’s College.", "../alumni/")]
    body = f"""
{M.page_head(R, "Become a Konkrete Kid", "Why Northampton, our home, the path, and how to start.", "showcase-arms-up", "40% 28%")}
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
    <p class="lede">Brayden Wenrich won a District XI junior high title in 2024. Two years later he was a state champion.</p>
  </div>
</section>
<section class="band">
  <div class="wrap split">
    {M.figure(R, "practice-room", "(min-width: 900px) 45vw, 100vw", "wide-fig")}
    <div class="prose"><h2>Our home</h2><p>Home matches in Pete Schneider Gym under the state championship banners, and daily practice in the wrestling room.</p><p><a class="text-link" href="../facilities/">See our home</a> · <a class="text-link" href="../coaching-staff/">Meet the coaches</a></p></div>
  </div>
</section>
<section class="band concrete" id="start" aria-labelledby="start-title">
  <div class="wrap">
    <h2 id="start-title">Start wrestling</h2>
    <div class="start-grid">
      <div class="note-card"><h3>Grades K–6</h3><p>Join the youth program. No experience needed.</p><a class="btn" href="mailto:{M.SITE['email']}?subject=Youth%20wrestling">Email about youth wrestling</a></div>
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
    off = M.COACHES["officers"]["list"]
    faq = [("When does the season start?", "The high school season begins in November and runs through the PIAA Championships in March. Dates post on the schedule page as soon as they’re released."),
           ("Where can I find the schedule?", 'On our <a href="../schedule/">schedule page</a> and the district athletics calendar, which also lists bus times and changes.'),
           ("Can parents watch youth practice?", "In the youth program, only each team’s coaching staff is in the practice room. Matches and tournaments are open to families and fans."),
           ("What if my child misses practice?", "In-season practice and competition attendance is required. Talk to your child’s coach about any special circumstances ahead of time; they’re handled case by case."),
           ("What does a wrestler need before the season?", "A PIAA physical on file with the district athletic office, plus the weight assessment the coaches schedule early in the season."),
           ("How do I reach a coach?", f'Email <a href="mailto:{M.SITE["email"]}">{M.SITE["email"]}</a> and we’ll get your message to the right coach.')]
    body = f"""
{M.page_head(R, "Family", "What parents and families need to know.", "senior-night", "50% 40%")}
<section class="band">
  <div class="wrap split even">
    <div class="prose">
      <h2>Season at a glance</h2>
      <ul class="results" role="list"><li><span>High school season</span><b>November – March</b></li><li><span>Postseason</span><b>District XI, Regional, PIAA</b></li><li><span>Home matches</span><b>Pete Schneider Gym</b></li><li><span>Banquet</span><b>Spring</b></li></ul>
      <p class="actions"><a class="btn" href="../schedule/">Schedule</a><a class="btn ghost dark-ink" href="{M.SITE['links']['district_calendar']}" rel="noopener">District calendar</a></p>
    </div>
    <div class="prose">
      <h2>Program expectations</h2>
      <p>We never sacrifice goodness for greatness. Wrestlers are expected to be at every in-season practice and competition, and to represent Northampton with integrity on and off the mat.</p>
      <p>In the youth program, only each team’s coaching staff is in the practice room, and in-season attendance is required: club practices and outside tournaments don’t replace team practice. Special circumstances are handled case by case.</p>
    </div>
  </div>
</section>
<section class="band concrete" id="faq" aria-labelledby="faq-title">
  <div class="wrap"><h2 id="faq-title">FAQs</h2><div class="faq">{''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faq)}</div></div>
</section>
<section class="band dark" id="booster" aria-labelledby="booster-title">
  <div class="wrap split even">
    <div class="prose">
      <h2 id="booster-title">Booster club</h2>
      <p>The {M.SITE['owner']} supports the program from youth to varsity: the awards banquet, the Charlie Lerch Memorial and Brandon M. Sommer Memorial scholarships, team gear, and more. Volunteers keep it all running.</p>
      <p><a class="btn" href="mailto:{M.SITE['email']}?subject=Volunteer">Volunteer with the club</a></p>
    </div>
    <div><h3 class="sub">Club officers</h3><ul class="results on-dark" role="list">{M.result_rows(off)}</ul></div>
  </div>
</section>
"""
    return M.page("family/index.html", "Family", "Information for Northampton wrestling parents and families: schedule, expectations, FAQs, and the booster club.", body, "family/", og_image="senior-night")


def build_alumni():
    R = "../"
    home = [("Mike Sommer", "Class of 1997 · varsity assistant"), ("Marcus Newsom", "Northampton alumnus · varsity assistant"),
            ("John Paukovits", "3x District XI champion · varsity assistant"), ("Ethan Szerencsits", "Class of 2020 · varsity assistant"),
            ("Braden Turner", "2008 District and Regional champion · junior high assistant"), ("Justin Haupt", "1998–99 District XI champion · junior high assistant")]
    body = f"""
{M.page_head(R, "Alumni", "Once a Konkrete Kid, always a Konkrete Kid.", "coaches-embrace", "60% 30%")}
<section class="band">
  <div class="wrap split even">
    <div class="prose">
      <h2>Where are they now?</h2>
      <p>We want to hear from every Konkrete Kid, from the 1940s to last spring. Where did wrestling take you? Did you wrestle in college, coach, serve, start a family of future Konkrete Kids?</p>
      <p>Send a few lines and a photo, then and now if you have them, and we’ll share alumni stories here.</p>
      <p><a class="btn" href="mailto:{M.SITE['email']}?subject=Alumni%20story">Share your story</a></p>
    </div>
    <div>
      <h2>Konkrete Kids who came home</h2>
      <ul class="results" role="list">{''.join(f'<li><span>{a}</span><b>{b}</b></li>' for a, b in home)}</ul>
    </div>
  </div>
</section>
<section class="band concrete" id="update" aria-labelledby="update-title">
  <div class="wrap prose"><h2 id="update-title">Update your information</h2><p>Get invited to alumni events and Coach’s Corner. Email your name, graduation year, and best contact info.</p><p><a class="btn" href="mailto:{M.SITE['email']}?subject=Alumni%20update&body=Name%3A%0AGraduation%20year%3A%0AEmail%3A%0APhone%20(optional)%3A">Update your info</a></p></div>
</section>
<section class="band dark" id="support" aria-labelledby="support-title">
  <div class="wrap prose"><h2 id="support-title">Support the program</h2><p>The {M.SITE['owner']} funds scholarships, gear, and the banquet. To donate, sponsor, or help organize an alumni night, email <a href="mailto:{M.SITE['email']}">{M.SITE['email']}</a>.</p></div>
</section>
"""
    return M.page("alumni/index.html", "Alumni", "Northampton wrestling alumni: share your story, update your information, and support the program.", body, "alumni/", og_image="coaches-embrace")


def build_follow():
    R = "../"
    body = f"""
{M.page_head(R, "Follow Northampton", "Coach’s Corner, match updates, and every Konkrete Kids channel in one place.")}
<section class="band dark"><div class="wrap">{follow_block(R, "nl-title")}</div></section>
"""
    return M.page("follow/index.html", "Follow", "Follow Northampton Wrestling: Coach’s Corner newsletter and social media.", body, "follow/")


def build_all(module):
    global M
    M = module
    urls = [build_roster(), build_results(), build_news(), build_photos(), build_videos(), build_timeline(),
            build_story(), build_facilities(), build_join(), build_family(), build_alumni(), build_follow()]
    return urls
