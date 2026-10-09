#!/usr/bin/env python3
"""Build the Northampton Wrestling site from the files in data/.

    python3 tools/build.py

Writes every page (index.html, high-school/index.html, ...), the Hall of
Champions data file, sitemap.xml and robots.txt. Edit the data files, then run
this again; never edit the generated HTML by hand.
"""
import csv, html, json, os, re, tomllib
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
e = html.escape


def load_toml(name):
    return tomllib.load(open(os.path.join(DATA, name), "rb"))


def load_csv(name):
    return list(csv.DictReader(open(os.path.join(DATA, name), newline="")))


SITE = load_toml("site.toml")
COACHES = load_toml("coaches.toml")
SEASONS = load_toml("seasons.toml")["season"]
PHOTOS = {p["id"]: p for p in load_toml("photos.toml")["photo"]}
MANIFEST = json.load(open(os.path.join(ROOT, "assets", "img", "photos", "manifest.json")))
STATS = load_csv("stats-2025-26.csv")
HALL = {
    "state": load_csv("hall/state-champions.csv"),
    "medals": load_csv("hall/state-placewinners.csv"),
    "regional": load_csv("hall/regional-champions.csv"),
    "district": load_csv("hall/district-champions.csv"),
}
RECORDS = load_csv("hall/season-records.csv")
HEAD_COACHES = load_csv("hall/head-coaches.csv")
HUNDRED = load_csv("hall/hundred-wins.csv")
# State medals won for other schools before transferring in. Shown on profiles with the
# school named; never counted in program totals, lists, or streaks.
OTHER = load_csv("hall/other-schools.csv")
TEAM_TITLES = load_csv("hall/team-titles.csv")
SEASON_VIDEOS = load_toml("season-videos.toml")
CUR = SEASONS[0]

NAV_GROUPS = [
    ("Program", [("story/", "Our Story"), ("coaching-staff/", "Coaches"), ("facilities/", "Our Home"),
                 ("high-school/", "Varsity"), ("junior-high/", "Junior High"), ("youth/", "Youth")]),
    ("Team", [("roster/", "Roster"), ("schedule/", "Schedule"), ("results/", "Results"), ("high-school/#stats-title", "Stats")]),
    ("Tradition", [("champions/", "Hall of Champions"), ("champions/#team-title", "Team Titles"),
                   ("champions/#hundred-title", "100-Win Club"), ("champions/#lists-title", "Record Book"),
                   ("timeline/", "Timeline"), ("seasons/", "Past Seasons")]),
    ("Media", [("news/", "News"), ("photos/", "Photos"), ("videos/", "Videos"), ("follow/", "Coach’s Corner")]),
    ("Family", [("family/", "Parent Information"), ("family/#faq", "FAQs"), ("family/#booster", "Booster Club")]),
    ("Alumni", [("alumni/", "Where Are They Now"), ("alumni/#update", "Update Your Information"), ("alumni/#support", "Support the Program")]),
    ("Join", [("join/", "Why Northampton"), ("join/#path", "The Path"), ("youth/", "Youth Wrestling"), ("join/#start", "Start Wrestling")]),
]
NAV = [("", "Home")] + [(h, l) for _, items in NAV_GROUPS for h, l in items if "#" not in h]
NAV = list(dict.fromkeys(NAV))


# Display-name aliases so one wrestler collects every honor in the Hall search
ALIASES = {"Gabe Ballard": "Gabriel Ballard"}

PLACE = {"1": "Champion", "2": "2nd", "3": "3rd", "4": "4th", "5": "5th", "6": "6th", "7": "7th", "8": "8th"}


# ------------------------------------------------------------------ helpers
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def ordinal_suffix(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def picture(R, pid, sizes="100vw", cls="", eager=False, alt=None, focus=None):
    """<picture> with WebP srcset and a JPEG fallback."""
    m = MANIFEST[pid]
    p = PHOTOS[pid]
    srcset = ", ".join(f"{R}assets/img/photos/{pid}-{w}.webp {w}w" for w, _ in m["widths"])
    fw, fh = m["fallback"]
    a = p.get("alt", "") if alt is None else alt
    style = f' style="object-position:{focus or p["focus"]}"' if (focus or p.get("focus")) else ""
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    c = f' class="{cls}"' if cls else ""
    return (f'<picture><source type="image/webp" srcset="{srcset}" sizes="{sizes}">'
            f'<img src="{R}assets/img/photos/{pid}.jpg" width="{fw}" height="{fh}" alt="{e(a)}"{c}{style} {load}></picture>')


def largest(R, pid):
    w, _ = MANIFEST[pid]["widths"][-1]
    return f"{R}assets/img/photos/{pid}-{w}.webp"


def figure(R, pid, sizes, cls="", caption=True):
    p = PHOTOS[pid]
    cap = p.get("caption", "") if caption else ""
    credit = p.get("credit")
    bits = []
    if cap:
        bits.append(e(cap))
    if credit:
        bits.append(f'<span class="credit">Photo: {e(credit)}</span>')
    fc = f"<figcaption>{' '.join(bits)}</figcaption>" if bits else ""
    return f'<figure class="{cls}">{picture(R, pid, sizes)}{fc}</figure>'


def gallery(R, ids, name):
    items = []
    for pid in ids:
        p = PHOTOS[pid]
        m = MANIFEST[pid]
        cap = p.get("caption", "")
        if p.get("credit"):
            cap = (cap + " " if cap else "") + f"Photo: {p['credit']}"
        items.append(
            f'<li><a href="{largest(R, pid)}" data-lightbox="{name}" data-caption="{e(cap)}" '
            f'data-w="{m["widths"][-1][0]}" data-h="{m["widths"][-1][1]}">'
            f'{picture(R, pid, "(min-width: 900px) 30vw, (min-width: 560px) 45vw, 100vw")}</a></li>')
    return f'<ul class="gallery" role="list">{"".join(items)}</ul>'


def icon(name):
    paths = {
        "instagram": '<path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 8.2A3.2 3.2 0 1 1 12 8.8a3.2 3.2 0 0 1 0 6.4zm5.3-9.7a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4zM22 7c-.1-1.6-.4-3-1.6-4.2S17.6 1.2 16 1.1C14.4 1 9.6 1 8 1.1 6.4 1.2 5 1.5 3.8 2.7S2.2 5.4 2.1 7C2 8.6 2 15.4 2.1 17c.1 1.6.4 3 1.6 4.2s2.6 1.5 4.2 1.6c1.6.1 6.4.1 8 0 1.6-.1 3-.4 4.2-1.6s1.5-2.6 1.6-4.2c.1-1.6.1-8.4.3-10zm-2 12.2a3.3 3.3 0 0 1-1.9 1.9c-1.3.5-4.4.4-5.9.4s-4.6.1-5.9-.4A3.3 3.3 0 0 1 4.4 19c-.5-1.3-.4-4.4-.4-5.9s-.1-4.6.4-5.9a3.3 3.3 0 0 1 1.9-1.9c1.3-.5 4.4-.4 5.9-.4s4.6-.1 5.9.4a3.3 3.3 0 0 1 1.9 1.9c.5 1.3.4 4.4.4 5.9s.1 4.6-.4 5.9z"/>',
        "x": '<path d="M18.2 2h3.4l-7.4 8.5L23 22h-6.8l-5.3-7-6.1 7H1.4l7.9-9.1L1 2h7l4.8 6.4L18.2 2zm-1.2 18h1.9L7.1 3.9H5.1L17 20z"/>',
        "facebook": '<path d="M14 8V6c0-.9.6-1.1 1-1.1h2.8V1H14C10.3 1 9.5 3.8 9.5 5.6V8H7v4h2.5v11H14V12h3.4l.5-4H14z"/>',
        "youtube": '<path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.6 15.6V8.4l6.3 3.6-6.3 3.6z"/>',
    }
    return f'<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[name]}</svg>'


SOCIAL_NAMES = {"instagram": "Instagram", "x": "X (Twitter)", "facebook": "Facebook", "youtube": "YouTube"}


def social_links():
    return "".join(
        f'<a href="{SITE["social"][k]}" rel="noopener" aria-label="Northampton Wrestling on {SOCIAL_NAMES[k]}">{icon(k)}</a>'
        for k in ("instagram", "x", "facebook", "youtube"))


LOGO = ''


def asset_ver(rel):
    """Short content hash so browsers fetch new CSS/JS whenever it changes."""
    import hashlib
    return hashlib.md5(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()[:8]


def page(path, title, desc, body, active=None, extra_head="", scripts=("site.js",), og_image="hero-circle", hero_header=False):
    depth = path.count("/")
    R = "../" * depth
    url = SITE["domain"] + "/" + (path[:-len("index.html")] if path.endswith("index.html") else path)
    full_title = f"{SITE['name']} | {SITE['nickname']}" if path == "index.html" else f"{title} | {SITE['name']}"
    groups = []
    for gi, (glabel, items) in enumerate(NAV_GROUPS):
        on = any(h.split("#")[0] == active for h, _ in items)
        links = "".join(f'<li><a href="{R}{h}"{" aria-current=\"page\"" if h == active else ""}>{l}</a></li>' for h, l in items)
        groups.append(f'<li class="has-sub{" is-active" if on else ""}"><button type="button" class="sub-btn" aria-expanded="false" aria-controls="sub-{gi}">{glabel}</button>'
                      f'<ul class="sub" id="sub-{gi}" role="list">{links}</ul></li>')
    nav = "".join(groups)
    og = SITE["domain"] + "/" + largest("", og_image)
    js = "".join(f'<script src="{R}assets/js/{s}?v={asset_ver("assets/js/" + s)}" defer></script>' for s in scripts)
    head_cls = " is-over-hero" if hero_header else ""
    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE['name']}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#141414">
<link rel="icon" href="{R}assets/img/icon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{R}assets/img/apple-touch-icon.png">
<link rel="manifest" href="{R}site.webmanifest">
<link rel="preload" href="{R}assets/fonts/anton-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{R}assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{R}assets/css/site.css?v={asset_ver("assets/css/site.css")}">
{extra_head}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head{head_cls}">
  <div class="wrap head-row">
    <a class="brand" href="{R or './'}" aria-label="{SITE['name']} home"><img class="mark" src="{R}assets/img/logo-96.png" srcset="{R}assets/img/logo-96.png 1x, {R}assets/img/logo-192.png 2x" width="56" height="48" alt=""><span>Northampton<br>Wrestling</span></a>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav"><span class="bars" aria-hidden="true"></span><span class="label">Menu</span></button>
    <nav class="site-nav" id="site-nav" aria-label="Main"><ul class="top" role="list">{nav}</ul><a class="follow-btn" href="{R}follow/">Follow</a></nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <img class="foot-logo" src="{R}assets/img/logo-192.png" srcset="{R}assets/img/logo-192.png 1x, {R}assets/img/logo-400.png 2x" width="120" height="103" alt="Northampton Konkrete Kids logo" loading="lazy">
      <p>Northampton wrestling since {SITE['established']}. {SITE['conference']}, {SITE['district']}.</p>
      <div class="social">{social_links()}</div>
    </div>
    <div>
      <h2>Contact</h2>
      <p><a href="mailto:{SITE['email']}">{SITE['email']}</a></p>
      <p>{SITE['phone_label']}: <a href="tel:+1{SITE['phone'].replace('-', '')}">{SITE['phone']}</a></p>
      <p>{SITE['school']}<br>{'<br>'.join(SITE['address'])}</p>
    </div>
    <div>
      <h2>Explore</h2>
      <ul role="list" class="foot-links">{''.join(f'<li><a href="{R}{items[0][0]}">{g}</a></li>' for g, items in NAV_GROUPS)}<li><a href="{R}follow/">Follow</a></li></ul>
    </div>
  </div>
  <div class="wrap foot-base">
    <p>&copy; <span data-year>2026</span> {SITE['owner']}</p>
  </div>
</footer>
{js}
</body>
</html>
"""
    dest = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(dest) or ROOT, exist_ok=True)
    open(dest, "w").write(out)
    return url


def section_head(title, intro="", level=2, id_=None):
    i = f' id="{id_}"' if id_ else ""
    p = f'<p class="lede">{intro}</p>' if intro else ""
    return f'<div class="sec-head"><h{level}{i}>{title}</h{level}>{p}</div>'


def page_head(R, title, intro, photo=None, focus=None, kicker=None):
    k = f'<p class="kicker">{kicker}</p>' if kicker else ""
    if photo:
        return (f'<header class="page-head has-photo">{picture(R, photo, "100vw", "bg", True, alt="", focus=focus)}'
                f'<div class="wrap">{k}<h1>{title}</h1><p class="lede">{intro}</p></div></header>')
    return f'<header class="page-head concrete"><div class="wrap">{k}<h1>{title}</h1><p class="lede">{intro}</p></div></header>'


def result_rows(rows):
    return "".join(f"<li><span>{e(a)}</span><b>{e(b)}</b></li>" for a, b in rows)


def place_cell(v):
    if not v:
        return '<td class="na">—</td>'
    cls = "gold" if v in ("Champion", "1st") else ("podium" if v in ("2nd", "3rd") else "")
    return f'<td class="{cls}">{e(v)}</td>'


def postseason_table(rows, caption):
    body = "".join(
        f"<tr><th scope=\"row\">{e(n)}{f' <span class=\"wt\">{w}</span>' if w else ''}</th>{place_cell(d)}{place_cell(r)}{place_cell(s)}</tr>"
        for n, w, d, r, s in rows)
    return (f'<div class="table-wrap" tabindex="0" role="region" aria-label="{e(caption)}"><table class="path"><caption>{caption}</caption>'
            f'<thead><tr><th scope="col">Wrestler</th><th scope="col">District XI</th><th scope="col">NE Regional</th><th scope="col">PIAA</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


CHAMPS = load_toml("hall/champions.toml")


def pennant(year, name, weight, small=False, R=None):
    """A state-champion banner. With R (path prefix) it links to the champion's page
    and shows the banner headshot when one is set in data/hall/champions.toml."""
    if R is None:
        return (f'<li class="pennant{" sm" if small else ""}"><span class="yr">{year}</span>'
                f'<span class="nm">{e(name)}</span><span class="wt">{e(weight)}</span></li>')
    c = CHAMPS.get(name, {})
    bid = c.get("banners", {}).get(str(year)) or c.get("banner")
    if bid:
        face = picture(R, bid, "160px", "pn-face", alt="")
    else:
        face = f'<span class="pn-face pn-logo"><img src="{R}assets/img/logo-96.png" alt="" width="56" height="48" loading="lazy"></span>'
    return (f'<li class="pennant linked{" has-face" if c.get("banner") else ""}"><a href="{R}champions/{slug(name)}/">'
            f'<span class="yr">{year}</span>{face}<span class="nm">{e(name)}</span><span class="wt">{e(weight)}</span>'
            f'<span class="visually-hidden">: read the story</span></a></li>')


# ------------------------------------------------------------------ hall math
def norm(n):
    return ALIASES.get(n, n)


def counts():
    c = {k: Counter(norm(r["wrestler"]) for r in HALL[k]) for k in HALL}
    medals = c["medals"] + c["state"]
    return c, medals


def multi_lists():
    """[(category, [(times, names), ...]), ...] for wrestlers with 2+ of an honor."""
    c, medals = counts()
    out = []
    for title, ctr in (("State medalists", medals), ("Regional champions", c["regional"]),
                       ("District XI champions", c["district"])):
        tiers = []
        for k in (4, 3, 2):
            names = sorted((n for n, v in ctr.items() if v == k), key=lambda s: s.split()[-1] + s)
            if names:
                tiers.append((k, names))
        out.append((title, tiers))
    return out


def eras():
    out = []
    for row in HEAD_COACHES:
        a = int(row["first_year"])
        b = int(row["last_year"]) if row["last_year"] else 9999
        inr = lambda k: sum(1 for r in HALL[k] if a <= int(r["year"]) <= b)
        out.append(dict(row, district=inr("district"), regional=inr("regional"), state=inr("state")))
    return out


TOTALS = {
    "state": len(HALL["state"]),
    "medals": len(HALL["state"]) + len(HALL["medals"]),
    "regional": len(HALL["regional"]),
    "district": len(HALL["district"]),
    "wins": sum(int(r["wins"]) for r in HEAD_COACHES),
    "seasons": sum(int(r["years"]) for r in HEAD_COACHES),
    "team_titles": len(TEAM_TITLES),
    "hundred": len(HUNDRED),
}


def medal_streak():
    yrs = {int(r["year"]) for k in ("state", "medals") for r in HALL[k]}
    end = max(yrs); y = end
    while y - 1 in yrs:
        y -= 1
    return y, end, end - y + 1


def end_year(span):
    tail = span.split("-")[-1]
    if not tail:
        return None
    yy = int(tail)
    return (1900 if yy >= 40 else 2000) + yy


TOTALS["streak"] = medal_streak()


def hall_json():
    people = defaultdict(lambda: {"honors": []})
    for k, label in (("state", "PIAA champion"), ("regional", "Northeast Regional champion"), ("district", "District XI champion")):
        for r in HALL[k]:
            n = norm(r["wrestler"])
            people[n]["honors"].append([int(r["year"]), label, r["weight"]])
    for r in HALL["medals"]:
        n = norm(r["wrestler"])
        p = int(r["place"])
        people[n]["honors"].append([int(r["year"]), f"PIAA {p}{ordinal_suffix(p)} place", r["weight"]])
    for r in OTHER:
        p = int(r["place"])
        people[norm(r["wrestler"])]["honors"].append([int(r["year"]), f"PIAA {p}{ordinal_suffix(p)} place", r["weight"], r["school"]])
    for r in HUNDRED:
        n = norm(r["wrestler"])
        y = end_year(r["years"]) or 2026
        people[n]["honors"].append([y, f"100-Win Club: {r['wins']} career wins" + (" and counting" if r["status"] == "active" else ""), ""])
    for r in RECORDS:
        n = norm(r["wrestler"])
        people[n]["honors"].append([int(r["year"]), f"School record list: {r['category'].lower()} ({r['value']})", ""])
    out = []
    for n, d in people.items():
        d["honors"].sort(key=lambda h: (h[0], h[1]))
        out.append({"name": n, "honors": d["honors"]})
    out.sort(key=lambda p: p["name"].split()[-1] + p["name"])
    return out


# ------------------------------------------------------------------ pages
def build_home():
    R = ""
    s = CUR
    wins = {r["wrestler"]: r for r in STATS}
    champ = lambda pid, name, wt, lines: (
        f'<article class="champ-card">{picture(R, pid, "(min-width: 900px) 40vw, 90vw")}'
        f'<div class="champ-body"><p class="champ-tag">PIAA champion at {wt} pounds</p><h3>{name}</h3>'
        f'<ul role="list">{"".join(f"<li>{l}</li>" for l in lines)}</ul></div></article>')
    w = wins["Brayden Wenrich"]
    b = wins["Gabe Ballard"]
    t = wins["Trey Wagner"]
    recent = HALL["state"][::-1]
    body = f"""
<section class="hero" aria-labelledby="hero-title">
  {picture(R, "hero-circle", "100vw", "hero-img", eager=True)}
  <div class="wrap hero-copy">
    <p class="script" aria-hidden="true">Konkrete Kids</p>
    <h1 id="hero-title">Northampton<br>Wrestling</h1>
    <p class="hero-sub">Since {SITE['established']}. {SITE['conference']}, {SITE['district']}.</p>
    <p class="hero-actions"><a class="btn" href="high-school/">2025–26 season recap</a><a class="btn ghost" href="champions/">Hall of Champions</a></p>
  </div>
</section>

<section class="facts" aria-label="2025–26 at a glance">
  <div class="wrap facts-row">
    <p><b>{s['dual_record']}</b> dual meet record</p>
    <p><b>3rd</b> at the PIAA State Tournament</p>
    <p><b>2</b> state champions</p>
    <p><b>3</b> Northeast Regional champions</p>
    <p><b>5</b> state qualifiers</p>
  </div>
</section>

<section class="band dark champs" aria-labelledby="champs-title">
  <div class="wrap">
    {section_head('<span id="champs-title">Two state champions</span>', 'Brayden Wenrich and Gabe Ballard won PIAA titles in Hershey in March 2026, the first time since 2004 that Northampton crowned two state champions in the same year.')}
    <div class="champ-grid">
      {champ("portrait-wenrich-2026", "Brayden Wenrich", "114", [f"{w['wins']}–{w['losses']} as a sophomore", "District XI, Northeast Regional, and PIAA champion", "Fastest pin of the season: 9 seconds", f"{w['career_wins']}–{w['career_losses']} career record"])}
      {champ("portrait-ballard-2026", "Gabe Ballard", "152", [f"{b['wins']}–{b['losses']} as a junior", "District XI, Northeast Regional, and PIAA champion", "114 takedowns, 238 team points", f"{b['career_wins']} career wins"])}
    </div>
    <div class="also">
      <article class="mini">{picture(R, "portrait-wagner-2026", "160px")}<div><h3>Trey Wagner</h3><p>Northeast Regional champion and state 7th at 139. Finished his career {t['career_wins']}–{t['career_losses']}.</p></div></article>
      <article class="mini">{picture(R, "portrait-sommer-2026", "160px")}<div><h3>Matthew Sommer</h3><p>State qualifier at 133.</p></div></article>
      <article class="mini">{picture(R, "portrait-chlebove-2026", "160px")}<div><h3>Carter Chlebove</h3><p>State qualifier at 160.</p></div></article>
    </div>
  </div>
</section>

<section class="moment" aria-label="Photo">
  <div class="wrap moment-split">
    <figure class="moment-photo">{picture(R, "trey-embrace", "(min-width: 760px) 440px, 90vw")}</figure>
    <div class="moment-text">
      <p class="moment-cap">The moment it all pays off.</p>
      <p class="moment-sub">{e(PHOTOS["trey-embrace"]["caption"])}</p>
    </div>
  </div>
</section>

<section class="band" aria-labelledby="about-title">
  <div class="wrap">
    <div class="prose">
      <h2 id="about-title">History, tradition, community</h2>
      <p>Northampton Wrestling began in 1945. More than 80 seasons later, the program runs from kindergarten through varsity, and every Konkrete Kid comes through the same room, the same expectations, and the same black and orange.</p>
      <p>Our mission is to give young people a supportive, demanding place to grow as wrestlers and as responsible, resilient, respectful members of the community. We never sacrifice goodness for greatness. Integrity and honor come first, and winning is the byproduct.</p>
      <p><a class="text-link" href="coaching-staff/">Meet the coaching staff</a></p>
    </div>
    {figure(R, "program-family", "(min-width: 1180px) 1100px, 100vw", "natural-fig program-fig")}
  </div>
</section>

<section class="band concrete" aria-labelledby="wall-title">
  <div class="wrap">
    {section_head('<span id="wall-title">The banner wall</span>', f'{TOTALS["state"]} PIAA state champions since 1955. These are the last ten.')}
    <ol class="pennants" role="list" reversed>{''.join(pennant(r['year'], norm(r['wrestler']), r['weight'], R=R) for r in recent[:10])}</ol>
    <div class="numbers">
      <p><b>{TOTALS['team_titles']}</b> PIAA team titles</p>
      <p><b>{TOTALS['state']}</b> individual state titles</p>
      <p><b>{TOTALS['medals']}</b> state medals</p>
      <p><b>{TOTALS['regional']}</b> regional titles</p>
      <p><b>{TOTALS['district']}</b> District XI titles</p>
      <p><b>{TOTALS['hundred']}</b> 100-win wrestlers</p>
      <p><b>{TOTALS['wins']}</b> dual meet wins</p>
    </div>
    <p><a class="btn" href="champions/">See every champion</a></p>
  </div>
</section>

<section class="band" aria-labelledby="levels-title">
  <div class="wrap">
    {section_head('<span id="levels-title">One program, every level</span>')}
    <div class="levels">
      <a class="level" href="high-school/">{picture(R, "team-mayhem", "(min-width: 900px) 33vw, 100vw")}<span><b>High school</b>Varsity and JV results, rosters, and stats</span></a>
      <a class="level" href="junior-high/">{picture(R, "jh-districts", "(min-width: 900px) 33vw, 100vw")}<span><b>Junior high</b>Grades 7 and 8, the bridge to the varsity room</span></a>
      <a class="level" href="youth/">{picture(R, "youth-champs", "(min-width: 900px) 33vw, 100vw")}<span><b>Youth</b>Grades K–6 in the Valley Elementary Wrestling League</span></a>
    </div>
  </div>
</section>

<section class="band dark" aria-labelledby="photos-title">
  <div class="wrap">
    {section_head('<span id="photos-title">2025–26 in photos</span>')}
    {gallery(R, ["ballard-raised", "wenrich-celebrates", "dark-stance", "ballard-100", "celebration", "practice-room"], "home")}
    <p><a class="text-link on-dark" href="high-school/#photos">More from the season</a></p>
  </div>
</section>

<section class="band quote-band">
  <div class="wrap">
    <blockquote class="arena"><p>“The credit belongs to the man who is actually in the arena, whose face is marred by dust and sweat and blood; who strives valiantly; who errs, who comes short again and again… and who at the worst, if he fails, at least fails while daring greatly.”</p><footer>Theodore Roosevelt</footer></blockquote>
  </div>
</section>
"""
    ld = {
        "@context": "https://schema.org", "@type": "SportsTeam", "name": "Northampton Konkrete Kids Wrestling",
        "sport": "Wrestling", "url": SITE["domain"] + "/", "foundingDate": "1945",
        "memberOf": {"@type": "SportsOrganization", "name": SITE["owner"]},
        "location": {"@type": "Place", "name": SITE["school"], "address": {"@type": "PostalAddress", "streetAddress": SITE["address"][0], "addressLocality": "Northampton", "addressRegion": "PA", "postalCode": "18067", "addressCountry": "US"}},
        "logo": SITE["domain"] + "/assets/img/logo-400.png", "email": SITE["email"], "sameAs": list(SITE["social"].values()),
    }
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script>\n'
    return page("index.html", "Home", "Northampton Area High School wrestling, the Konkrete Kids: results, rosters, schedules, and every champion since 1945.", body, "", head, hero_header=True)


def build_high_school():
    R = "../"
    s = CUR
    leaders = {}
    cols = [("wins", "Wins"), ("falls", "Pins"), ("tech_falls", "Tech falls"), ("major_decisions", "Major decisions"), ("takedowns", "Takedowns"), ("team_points_duals", "Dual team points")]
    for k, _ in cols:
        leaders[k] = max(int(r[k]) for r in STATS)
    rows = []
    for r in sorted(STATS, key=lambda r: (-int(r["wins"]), r["wrestler"])):
        cells = "".join(
            f'<td data-v="{r[k]}"{" class=\"lead\"" if int(r[k]) == leaders[k] and int(r[k]) > 0 else ""}>{r[k]}</td>'
            for k, _ in cols[1:])
        rows.append(f'<tr><th scope="row" data-v="{e(r["wrestler"].split()[-1])}">{e(r["wrestler"])}</th>'
                    f'<td data-v="{r["wins"]}"{" class=\"lead\"" if int(r["wins"]) == leaders["wins"] else ""}>{r["wins"]}–{r["losses"]}</td>{cells}'
                    f'<td data-v="{r["career_wins"]}">{r["career_wins"]}–{r["career_losses"]}</td></tr>')
    head = "".join(f'<th scope="col" aria-sort="none"><button type="button">{l}</button></th>' for l in
                   ["Wrestler", "Record"] + [l for _, l in cols[1:]] + ["Career"])
    tw = sum(int(r["wins"]) for r in STATS)
    tl = sum(int(r["losses"]) for r in STATS)
    tot = lambda k: sum(int(r[k]) for r in STATS)
    stats_table = (f'<div class="table-wrap"><table class="sortable stats"><caption>2025–26 varsity final stats. Select a column heading to sort. Highlighted numbers led the team.</caption>'
                   f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody>'
                   f'<tfoot><tr><th scope="row">Team</th><td>{tw}–{tl}</td><td>{tot("falls")}</td><td>{tot("tech_falls")}</td><td>{tot("major_decisions")}</td><td>{tot("takedowns")}</td><td>{tot("team_points_duals")}</td><td></td></tr></tfoot></table></div>')

    seniors = "".join(
        f'<li><h3>{e(n)}</h3><p class="wt">{w} lb</p><p class="next">Next: {e(nx)}</p>'
        + (f'<blockquote><p>“{e(q)}”</p><footer>A Coach Provini saying he won’t forget</footer></blockquote>' if q else "") + "</li>"
        for n, w, nx, q in s["seniors"])
    awards = "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in s["awards"])
    medal_card = lambda pid, name, line: (f'<article class="medalist">{picture(R, pid, "(min-width: 900px) 18vw, 45vw")}'
                                         f'<h3>{name}</h3><p>{line}</p></article>')
    body = f"""
{page_head(R, "High School", "Northampton Area High School boys wrestling: varsity and JV.", "showcase-arms-up", "45% 12%")}

<section class="band" aria-labelledby="now-title">
  <div class="wrap split narrow-right">
    <div class="prose">
      <h2 id="now-title">2026–27</h2>
      <p>The new season starts this winter. The roster, lineup, and results will be posted here as the season goes.</p>
      <p>Both of last season’s state champions were underclassmen: Brayden Wenrich wrestled 2025–26 as a sophomore and Gabe Ballard as a junior.</p>
      <p class="actions"><a class="btn" href="../schedule/">Schedule</a><a class="btn ghost dark-ink" href="../coaching-staff/">Coaching staff</a></p>
    </div>
    {figure(R, "showcase-roar", "(min-width: 900px) 40vw, 100vw", "tall-fig")}
  </div>
</section>

<section class="band dark" aria-labelledby="recap-title">
  <div class="wrap">
    {section_head('<span id="recap-title">2025–26 season recap</span>', s["headline"])}
    <div class="facts-row on-dark">
      <p><b>{s['dual_record']}</b> dual meets</p>
      <p><b>3rd</b> PIAA State Tournament</p>
      <p><b>3rd</b> Northeast Regional</p>
      <p><b>3rd</b> District XI</p>
      <p><b>{tw}–{tl}</b> individual record</p>
    </div>
    <div class="medalists">
      {medal_card("portrait-wenrich-2026", "Brayden Wenrich", "PIAA champion, 114")}
      {medal_card("portrait-ballard-2026", "Gabe Ballard", "PIAA champion, 152")}
      {medal_card("portrait-wagner-2026", "Trey Wagner", "Regional champion, PIAA 7th, 139")}
      {medal_card("portrait-sommer-2026", "Matthew Sommer", "PIAA qualifier, 133")}
      {medal_card("portrait-chlebove-2026", "Carter Chlebove", "PIAA qualifier, 160")}
    </div>
  </div>
</section>

<section class="band" aria-labelledby="path-title">
  <div class="wrap split even">
    <div>
      <h2 id="path-title">The road to Hershey</h2>
      {postseason_table(s["postseason"], "2026 postseason results by wrestler")}
    </div>
    <div>
      <h2>Team finishes</h2>
      <ul class="results" role="list">{result_rows(s["team_finishes"])}</ul>
      <h3 class="sub">{s['jv_title']}</h3>
      <ul class="results" role="list">{result_rows(s["jv"])}</ul>
    </div>
  </div>
</section>

<section class="band concrete" aria-labelledby="stats-title">
  <div class="wrap">
    <h2 id="stats-title">Final stats</h2>
    {stats_table}
  </div>
</section>

<section class="band" aria-labelledby="awards-title">
  <div class="wrap">
    <h2 id="awards-title">Season awards</h2>
    <dl class="awards">{awards}</dl>
    <div class="split even top">
      <div>
        <h3 class="sub">Eastern Pennsylvania Conference all-stars</h3>
        <ul class="results" role="list">{result_rows(s["epc"])}</ul>
        <h3 class="sub">Never pinned</h3>
        <p>{e(", ".join(s["never_pinned"]))}</p>
      </div>
      <div>
        <h3 class="sub">Charlie Lerch Memorial Scholarships</h3>
        <p>{e(", ".join(s["lerch"]))}</p>
        <h3 class="sub">40 Point Club</h3>
        <ul class="results" role="list">{result_rows(s["forty_point"])}</ul>
      </div>
    </div>
  </div>
</section>

<section class="band dark" aria-labelledby="seniors-title">
  <div class="wrap">
    {section_head('<span id="seniors-title">Thank you, Class of 2026</span>', "Six seniors, and where they’re headed next.")}
    <ul class="seniors" role="list">{seniors}</ul>
  </div>
</section>

<section class="band" aria-labelledby="photos-title" id="photos">
  <div class="wrap">
    <h2 id="photos-title">The season in photos</h2>
    {gallery(R, s["gallery"], "season")}
  </div>
</section>

<section class="band concrete" aria-labelledby="roster-title">
  <div class="wrap split even">
    <div>
      <h2 id="roster-title">2025–26 roster</h2>
      <dl class="roster">{"".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in s["roster"])}</dl>
    </div>
    <div class="prose">
      <h2>Program awards</h2>
      <details><summary>40 Point Club</summary><p>Wrestlers who score 40 team points in dual meets in a season earn a winter jacket in year one, a spring jacket in year two, a hoodie in year three, and a scholarship in year four.</p></details>
      <details><summary>Chris Gmitter Picture Plaque Awards</summary><p>Regional qualifiers receive a plaque. District champions, regional champions, and state qualifiers receive a picture plaque, and district, regional, and state placewinners have their names added to the plaques in the wrestling room.</p></details>
      <details><summary>Charlie Lerch Memorial Scholarship</summary><p>Awarded to graduating seniors who wrestled in the Northampton program for at least three seasons, including senior year, and who enroll in higher education.</p></details>
      <details><summary>Brandon M. Sommer Memorial Scholarship</summary><p>A $500 award to the senior, a three-year member of the team, with the highest combined score for GPA and District, Regional, and State placement.</p></details>
      <p><a class="text-link" href="../seasons/">Earlier seasons</a></p>
    </div>
  </div>
</section>
"""
    return page("high-school/index.html", "High School", "Northampton High School wrestling: 2025–26 results, state champions, final stats, awards, and the Class of 2026.", body, "high-school/", og_image="team-mayhem")


def build_schedule():
    R = "../"
    body = f"""
{page_head(R, "Schedule", "Varsity, JV, and junior high match schedules for 2026–27.")}
<section class="band">
  <div class="wrap split narrow-right">
    <div class="prose">
      <h2>2026–27 schedule</h2>
      <p>The season schedule will be posted here once it is final. Until then, the district’s athletics calendar is the official source for every Northampton team, including bus times and changes.</p>
      <p class="actions"><a class="btn" href="{SITE['links']['district_calendar']}" rel="noopener">District athletics calendar</a><a class="btn ghost dark-ink" href="{SITE['links']['district_athletics']}" rel="noopener">Northampton athletics website</a></p>
      <h2>Follow along on match day</h2>
      <p>Results, lineups, and photos go up on the team’s social accounts during the season.</p>
      <div class="social dark-ink">{social_links()}</div>
    </div>
    <aside class="note-card">
      <h3>Postseason path</h3>
      <ol class="steps">
        <li><b>District XI AAA Championships</b><span>Top finishers advance</span></li>
        <li><b>PIAA Northeast Regional AAA</b><span>Top finishers advance</span></li>
        <li><b>PIAA Championships</b><span>Giant Center, Hershey</span></li>
      </ol>
    </aside>
  </div>
</section>
"""
    return page("schedule/index.html", "Schedule", "2026–27 Northampton wrestling schedules for varsity, JV, and junior high.", body, "schedule/")


def build_junior_high():
    R = "../"
    jh = CUR["junior_high"]
    staff = COACHES["junior_high"]["staff"]
    body = f"""
{page_head(R, "Junior High", "Grades 7 and 8. Where Konkrete Kids learn what the varsity room expects.", "jh-districts", "50% 35%")}
<section class="band">
  <div class="wrap split even">
    <div>
      <h2>2026–27 coaching staff</h2>
      <ul class="results" role="list">{result_rows(staff)}</ul>
      <p class="fine">Coaches Braden Turner and Justin Haupt are both former District XI and Northeast Regional champions for Northampton.</p>
    </div>
    <div>
      <h2>2025–26 recap</h2>
      <ul class="results" role="list"><li><span>Dual meet record</span><b>{jh['record']}</b></li>{result_rows(jh['finishes'])}</ul>
    </div>
  </div>
</section>
<section class="band dark">
  <div class="wrap split even">
    <div>
      <h2>2026 District XI placewinners</h2>
      <ul class="results on-dark" role="list">{result_rows(jh['placewinners'])}</ul>
    </div>
    <div class="prose">
      <h2>Recent history</h2>
      <p>In 2023–24 the junior high went 13–1 and won the District XI Junior High Tournament team title under Coach Joe Tocci. Three of that team’s district champions, Brayden Wenrich, Davi Glykas, and Carter Chlebove, were in the varsity lineup two seasons later, and Wenrich won a state title.</p>
    </div>
  </div>
</section>
"""
    return page("junior-high/index.html", "Junior High", "Northampton junior high wrestling: coaching staff, results, and district placewinners.", body, "junior-high/", og_image="jh-districts")


def build_youth():
    R = "../"
    body = f"""
{page_head(R, "Youth Wrestling", "Grades K–6. Where every Konkrete Kid starts.", "youth-champs", "50% 18%")}
<section class="band">
  <div class="wrap split narrow-right">
    <div class="prose">
      <h2>Northampton youth wrestling</h2>
      <p>Our youth program competes in the Valley Elementary Wrestling League (VEWL) for wrestlers in kindergarten through 6th grade. More than 100 kids wrestle each year on three teams:</p>
      <ul class="results" role="list"><li><span>Northampton Black</span><b>Varsity and JV</b></li><li><span>Northampton Orange</span><b>Varsity and JV</b></li><li><span>Novice</span><b>First-time wrestlers</b></li></ul>
      <p>The goal is simple: carry on the tradition of Northampton wrestling, teach strong fundamentals, and build friendships and a community that last long after the season ends. Many of today’s varsity wrestlers and coaches started right here.</p>
    </div>
    <aside class="note-card">
      <h3>Join the Konkrete Kids</h3>
      <p>Registration runs through the NAA youth program. Email us and we’ll send the current registration link and season details.</p>
      <p><a class="btn" href="mailto:{SITE['email']}?subject=Youth%20wrestling%20registration">Email about registration</a></p>
    </aside>
  </div>
</section>
<section class="band concrete">
  <div class="wrap">
    <h2>Questions families ask</h2>
    <div class="faq">
      <details><summary>Who can wrestle?</summary><p>Boys and girls in kindergarten through 6th grade.</p></details>
      <details><summary>Does my child need experience?</summary><p>No. The Novice team is for first-time wrestlers.</p></details>
      <details><summary>What happens after 6th grade?</summary><p>Wrestlers move up to the <a href="../junior-high/">junior high team</a> in grades 7 and 8, then to the <a href="../high-school/">high school</a> program.</p></details>
      <details><summary>Who do I contact?</summary><p>Email <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p></details>
    </div>
  </div>
</section>
<section class="band">
  <div class="wrap">
    <div class="duo">
      {figure(R, "youth-autographs", "(min-width: 900px) 45vw, 100vw")}
      {figure(R, "youth-mat", "(min-width: 900px) 45vw, 100vw")}
    </div>
  </div>
</section>
"""
    return page("youth/index.html", "Youth", "Northampton youth wrestling for grades K–6 in the Valley Elementary Wrestling League.", body, "youth/", og_image="youth-champs")


def build_coaches():
    R = "../"
    h = COACHES["head"]

    def coach_card(c):
        if c["photo"]:
            ph = picture(R, c["photo"], "120px", "avatar")
        else:
            ini = "".join(x[0] for x in c["name"].split())
            ph = f'<span class="avatar initials" aria-hidden="true">{ini}</span>'
        return f'<article class="coach">{ph}<div><h3>{e(c["name"])}</h3><p class="role">{e(c["role"])}</p><p>{e(c["bio"])}</p></div></article>'

    off = COACHES["officers"]
    body = f"""
{page_head(R, "Coaching Staff", "The coaches who run the room, from the varsity to the junior high.", "coaches-embrace", "60% 8%")}
<section class="band">
  <div class="wrap head-coach">
    <figure class="hc-photo">{picture(R, h['photo'], "(min-width: 900px) 30vw, 70vw")}</figure>
    <div class="prose">
      <p class="role">Head coach since {h['since']}</p>
      <h2>{h['name']}</h2>
      {''.join(f'<p>{e(p)}</p>' for p in h['bio'])}
    </div>
  </div>
  <div class="wrap">
    <div class="facts-row light">
      <p><b>{h['record']}</b> dual record</p>
      <p><b>{h['district_champs']}</b> District XI champions</p>
      <p><b>{h['regional_champs']}</b> regional champions</p>
      <p><b>{h['state_champs']}</b> PIAA champions</p>
      <p><b>{h['placewinners']}</b> state placewinners</p>
    </div>
    <p class="fine">At Northampton, through the 2025–26 season.</p>
  </div>
</section>
<section class="band concrete">
  <div class="wrap">
    <h2>Varsity assistants</h2>
    <div class="coaches">{''.join(coach_card(c) for c in COACHES['varsity'])}</div>
  </div>
</section>
<section class="band dark">
  <div class="wrap">
    <h2>Junior high staff</h2>
    <ul class="results on-dark jh-staff" role="list">{result_rows(COACHES['junior_high']['staff'])}</ul>
  </div>
</section>
<section class="band">
  <div class="wrap">
    <div class="trio">
      {figure(R, "coach-embrace", "(min-width: 900px) 30vw, 100vw")}
      {figure(R, "bench-final-seconds", "(min-width: 900px) 30vw, 100vw")}
      {figure(R, "staff-corner", "(min-width: 900px) 30vw, 100vw")}
    </div>
  </div>
</section>
"""
    return page("coaching-staff/index.html", "Coaching Staff", "Northampton wrestling coaching staff: head coach Joe Provini, varsity assistants, and junior high coaches.", body, "coaching-staff/", og_image="coaches-embrace")


def medals_chart():
    decades = Counter()
    for k in ("state", "medals"):
        for r in HALL[k]:
            decades[int(r["year"]) // 10 * 10] += 1
    ds = list(range(1950, 2030, 10))
    mx = max(decades.values())
    top = (mx + 9) // 10 * 10
    W, H, pl, pb, pt = 640, 260, 34, 28, 12
    bw = 24
    step = (W - pl - 10) / len(ds)
    bars, labels = [], []
    for i, d in enumerate(ds):
        v = decades.get(d, 0)
        x = pl + step * i + (step - bw) / 2
        bh = (H - pb - pt) * v / top
        y = H - pb - bh
        r = min(4, bh)
        if v:
            bars.append(
                f'<g class="bar" tabindex="0" data-tip="{d}s: {v} state medal{"s" if v != 1 else ""}">'
                f'<rect class="hit" x="{x - (step - bw) / 2 + 2:.1f}" y="{pt}" width="{step - 4:.1f}" height="{H - pb - pt}"/>'
                f'<path d="M{x:.1f},{H - pb} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + bw - r:.1f} Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} V{H - pb} Z"/>'
                f'<text class="val" x="{x + bw / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle">{v}</text></g>')
        labels.append(f'<text x="{x + bw / 2:.1f}" y="{H - 8}" text-anchor="middle">{d}s</text>')
    grid = "".join(
        f'<line x1="{pl}" x2="{W - 6}" y1="{H - pb - (H - pb - pt) * g / top:.1f}" y2="{H - pb - (H - pb - pt) * g / top:.1f}"/>'
        f'<text class="tick" x="{pl - 8}" y="{H - pb - (H - pb - pt) * g / top + 4:.1f}" text-anchor="end">{g}</text>'
        for g in range(0, top + 1, 10))
    best = ", ".join(f"{d}s ({decades[d]})" for d in sorted(decades, key=lambda d: -decades[d])[:2])
    rows = "".join(f"<tr><th scope=\"row\">{d}s</th><td>{decades.get(d, 0)}</td></tr>" for d in ds)
    return f"""<figure class="chart">
  <figcaption><b>PIAA medals by decade</b> Champions and placewinners, by the year of the state tournament.</figcaption>
  <div class="chart-box"><svg viewBox="0 0 {W} {H}" role="img" aria-label="Bar chart of Northampton PIAA state medals by decade. Most medals: {best}.">
    <g class="grid">{grid}</g><g class="bars">{''.join(bars)}</g><g class="xl">{''.join(labels)}</g></svg>
    <div class="tip" role="status" hidden></div></div>
  <details class="chart-data"><summary>Show as a table</summary><table><thead><tr><th scope="col">Decade</th><th scope="col">Medals</th></tr></thead><tbody>{rows}</tbody></table></details>
</figure>"""


def build_champions():
    R = "../"
    st = HALL["state"][::-1]
    medals = [dict(r, place="1") for r in HALL["state"]] + HALL["medals"]
    medals.sort(key=lambda r: (-int(r["year"]), int(r["place"]), r["wrestler"]))

    def tbl(id_, cap, head, rows):
        th = "".join(f'<th scope="col">{x}</th>' for x in head)
        return (f'<div class="table-wrap"><table class="hall" id="{id_}"><caption>{cap}</caption><thead><tr>{th}</tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')

    tr = lambda r, extra="": (f'<tr data-name="{e(norm(r["wrestler"]))}"><td>{r["year"]}</td><th scope="row">{e(r["wrestler"])}</th>'
                              f'<td>{r["weight"]}</td>{extra}</tr>')
    t_medals = tbl("t-medals", "PIAA state medalists, newest first", ["Year", "Wrestler", "Weight", "Place"],
                   "".join(tr(r, f'<td class="{"gold" if r["place"] == "1" else ""}">{PLACE[r["place"]]}</td>') for r in medals))
    t_reg = tbl("t-reg", "Northeast Regional champions, newest first", ["Year", "Wrestler", "Weight"], "".join(tr(r) for r in HALL["regional"][::-1]))
    t_dist = tbl("t-dist", "District XI champions, newest first", ["Year", "Wrestler", "Weight"], "".join(tr(r) for r in HALL["district"][::-1]))

    word = {4: "Four-time", 3: "Three-time", 2: "Two-time"}
    multi = "".join(
        f'<section class="mt-group"><h3>{t}</h3>' + "".join(
            f'<div class="mt-tier"><h4><span class="mt-x" aria-hidden="true">{k}×</span>{word[k]}'
            f'<span class="mt-n">{len(n)} wrestler{"s" * (len(n) != 1)}</span></h4><ul class="mt-names" role="list">'
            + "".join(f"<li>{e(x)}</li>" for x in n) + "</ul></div>" for k, n in tiers) + "</section>"
        for t, tiers in multi_lists())

    def rec(cat):
        rows = [r for r in RECORDS if r["category"] == cat]
        return (f'<div><h3>{cat}</h3><ol class="records" role="list">'
                + "".join(f'<li><span>{e(r["wrestler"])} <i>{r["year"]}</i></span><b>{r["value"]}</b></li>' for r in rows) + "</ol></div>")
    records = "".join(rec(c) for c in dict.fromkeys(r["category"] for r in RECORDS))

    er = eras()
    coach_rows = "".join(
        f'<tr><th scope="row">{e(x["coach"])}</th><td>{x["seasons"]}</td><td>{x["years"]}</td>'
        f'<td>{x["wins"]}–{x["losses"]}{"–" + x["ties"] if x["ties"] != "0" else ""}</td><td>{x["district"]}</td><td>{x["regional"]}</td><td>{x["state"]}</td></tr>'
        for x in er)
    tw = sum(int(x["wins"]) for x in er); tl = sum(int(x["losses"]) for x in er); tt = sum(int(x["ties"]) for x in er)
    coach_tbl = (f'<div class="table-wrap"><table class="hall"><caption>Head coaches since 1945. Championship counts are tallied from the lists on this page.</caption>'
                 f'<thead><tr><th scope="col">Coach</th><th scope="col">Seasons</th><th scope="col">Years</th><th scope="col">Dual record</th><th scope="col">District XI</th><th scope="col">Regional</th><th scope="col">PIAA</th></tr></thead>'
                 f'<tbody>{coach_rows}</tbody><tfoot><tr><th scope="row">All-time</th><td></td><td>{TOTALS["seasons"]}</td><td>{tw}–{tl}–{tt}</td><td>{TOTALS["district"]}</td><td>{TOTALS["regional"]}</td><td>{TOTALS["state"]}</td></tr></tfoot></table></div>'
                 '<p class="fine">Joe Provini’s record is through the 2025–26 season.</p>')

    tabs = [("medals", "State medalists", t_medals), ("regional", "Regional champions", t_reg),
            ("district", "District XI champions", t_dist), ("multi", "Multi-time honors", f'<div class="multi">{multi}</div>'),
            ("records", "Season records", f'<div class="records-grid">{records}</div>'), ("coaches", "Head coaches", coach_tbl)]
    tablist = "".join(f'<button type="button" role="tab" id="tab-{k}" aria-controls="panel-{k}" aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else " tabindex=\"-1\""}>{l}</button>'
                      for i, (k, l, _) in enumerate(tabs))
    panels = "".join(f'<div class="panel" role="tabpanel" id="panel-{k}" aria-labelledby="tab-{k}" tabindex="0"{"" if i == 0 else " hidden"}>{c}</div>'
                     for i, (k, _, c) in enumerate(tabs))
    open(os.path.join(ROOT, "assets", "data", "hall.json"), "w").write(json.dumps(hall_json(), separators=(",", ":")))
    body = f"""
{page_head(R, "Hall of Champions", "Every Konkrete Kid who has won a District XI, Northeast Regional, or PIAA title or medaled at the state tournament, from 1948 to today.")}
<section class="band" aria-labelledby="team-title">
  <div class="wrap">
    {section_head(f'<span id="team-title">{TOTALS["team_titles"]} PIAA team titles</span>', f'Northampton won the team title at the PIAA Class AAA championships seven times between 1993 and 2004. Select a banner for that season. The program has also had at least one state medalist every year since {TOTALS["streak"][0]}, {TOTALS["streak"][2]} straight seasons.')}
    <ol class="team-banners" role="list">{"".join(f'<li class="tbanner"><span class="t1">Northampton Wrestling</span><span class="t2">PIAA State Champions</span><span class="t3">AAA</span><a class="yr" href="{R}champions/team/{int(r["season"][:4]) + 1}/"><span class="visually-hidden">The </span>{e(r["season"])}<span class="visually-hidden"> team title season</span></a><span class="tb-more" aria-hidden="true">The season ›</span></li>' for r in TEAM_TITLES)}</ol>
  </div>
</section>
<section class="band dark wall-band" aria-labelledby="wall-title">
  <div class="wrap">
    {section_head(f'<span id="wall-title">{TOTALS["state"]} state champions</span>', "The banner wall, newest first. Select a banner for that champion’s story.")}
    <ol class="pennants full" role="list" reversed>{''.join(pennant(r['year'], norm(r['wrestler']), r['weight'], R=R) for r in st)}</ol>
  </div>
</section>
<section class="band" aria-labelledby="find-title">
  <div class="wrap split even">
    <div class="finder">
      <h2 id="find-title">Find a wrestler</h2>
      <label for="q">Name</label>
      <input id="q" type="search" autocomplete="off" placeholder="Try Ecklof, Chlebove, or Wagner" aria-describedby="q-help">
      <p id="q-help" class="fine">Shows every title, medal, and school record for that wrestler, and filters the tables below.</p>
      <div id="results" class="profiles" aria-live="polite"></div>
    </div>
    {medals_chart()}
  </div>
</section>
<section class="band" aria-labelledby="hundred-title">
  <div class="wrap">
    {section_head(f'<span id="hundred-title">The 100-Win Club</span>', f'{TOTALS["hundred"]} Konkrete Kids have won at least 100 varsity matches, as listed on the banners in the gym. Josh Haines holds the career record with 157.')}
    <ol class="hundred" role="list">{"".join(f'<li{" class=\"active\"" if r["status"] == "active" else ""}><span class="nm">{e(r["wrestler"])}</span><span class="yrs">{e(r["years"].replace("-", "–")) + ("present" if r["status"] == "active" else "")}</span><b>{r["wins"]}{"<sup>*</sup>" if r["status"] == "active" else ""}</b></li>' for r in HUNDRED)}</ol>
    <p class="fine">* Still wrestling. Career wins through the 2025–26 season.</p>
  </div>
</section>
<section class="band concrete" aria-labelledby="lists-title">
  <div class="wrap">
    <h2 id="lists-title">The record book</h2>
    <div class="tabs" role="tablist" aria-label="Record book">{tablist}</div>
    {panels}
    <p class="fine">Lists come from the Northampton Wrestling banquet programs, the banners in the gym, and PA-Wrestling.com team history. Missing or misspelled names? Email <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p>
  </div>
</section>
"""
    return page("champions/index.html", "Hall of Champions", "Northampton wrestling’s PIAA champions, state medalists, regional and District XI champions, season records, and head coaches since 1945.", body, "champions/", scripts=("site.js", "hall.js"), og_image="portrait-ballard-2026")


def season_phrases(facts, title):
    """Plain-English phrases from season_facts, e.g. '3 state champions'."""
    out, team = [], []
    for a, b in facts:
        if a == "Dual record":
            continue
        if a == "PIAA team":
            out.append("PIAA team champions" if title else f"{b.replace(' place', '')} at the PIAA Championships")
        elif a in ("State duals", "District XI duals"):
            out.append(f"{a} {b.lower()}")
        elif a in ("District XI team", "Regional team"):
            team.append(a.replace(" team", ""))
        elif b.isdigit():
            n = int(b)
            out.append(f"{n} {a[:-1] if n == 1 else a}".replace(" champions", " champions").lower().replace("district xi", "District XI"))
    if team:
        out.insert(1 if out and out[0].startswith(("PIAA", "1", "2", "3", "4", "5", "6", "7", "8", "9")) and "PIAA" in out[0] else 0,
                   " and ".join(team) + " team champions")
    return out


def season_videos(sid, label, heading="h3"):
    """Highlight video(s) for a season from data/season-videos.toml (facade, loads YouTube on click)."""
    vids = SEASON_VIDEOS.get(sid, [])
    if not vids:
        return ""
    many = len(vids) > 1
    cards = "".join(
        f'<div class="video-facade single" data-ytv="{v["id"]}"><img class="vf-img" src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="" loading="lazy">'
        f'<button type="button" class="vf-play"><span aria-hidden="true">▶</span> {label} highlights'
        + (f' · part {v["part"]}' if v["part"] and many else "") + "</button></div>" for v in vids)
    title = "Season highlight videos" if many else "Season highlight video"
    cls = ' class="sub"' if heading == "h3" else ""
    return f'<{heading}{cls}>{title}</{heading}><div class="season-vids{" many" if many else ""}">{cards}</div>'


PAWR = {f'{x["season"][:4]}-{x["season"][7:]}': x for x in json.load(open(os.path.join(DATA, "hall", "pawrestling-seasons.json")))["seasons"]}
TITLE_YEARS = {int(r["season"][:4]) + 1 for r in TEAM_TITLES}


def season_coach(y):
    for c in HEAD_COACHES:
        if int(c["first_year"]) <= y <= int(c["last_year"] or 9999):
            return c["coach"]
    return ""


def season_list():
    """Every season, newest first: (sid, label, end_year, pawr_row, detailed_entry_or_None)."""
    detail = {s["id"]: s for s in SEASONS}
    out = []
    for sid in sorted(set(PAWR) | set(detail), reverse=True):
        y = int(sid[:4]) + 1
        out.append((sid, f"{sid[:4]}–{sid[5:]}", y, PAWR.get(sid, {"record": "", "league_record": "", "finishes": [], "tournaments": [], "duals": []}), detail.get(sid)))
    return out


def season_facts(sid, y, pw, d):
    """Short facts for the index card and the season header. Only what the sources show."""
    f = []
    rec = d["dual_record"] if d and d.get("dual_record") else (pw["record"] if pw["record"] and len(pw["duals"]) >= 8 else "")
    if rec:
        f.append(("Dual record", rec))
    fin = dict(pw["finishes"])
    if y in TITLE_YEARS:
        f.append(("PIAA team", "State champions"))
    elif fin.get("PIAA Championships"):
        f.append(("PIAA team", f'{fin["PIAA Championships"]} place'))
    for x in pw["duals"]:
        name = x["opponent"] + " " + x["event"]
        if ("Championship Final" in name or "(Finals)" in name) and ("PIAA" in name or "District" in name):
            f.append(("State duals" if "PIAA" in name else "District XI duals", "Champions" if x["result"].startswith("W") else "Runner-up"))
    for st, lab in (("District XI tournament", "District XI team"), ("Northeast Regional", "Regional team")):
        if fin.get(st) == "1st":
            f.append((lab, "Champions"))
    n_st = sum(int(r["year"]) == y for r in HALL["state"])
    n_md = n_st + sum(int(r["year"]) == y for r in HALL["medals"])
    if n_st:
        f.append(("State champions", str(n_st)))
    if n_md > n_st:
        f.append(("State medalists", str(n_md)))
    if not n_md:
        for k, lab in (("regional", "Regional champions"), ("district", "District XI champions")):
            n = sum(int(r["year"]) == y for r in HALL[k])
            if n:
                f.append((lab, str(n)))
    return f


def season_videos(sid, label, heading="h3"):
    """Highlight video(s) for a season from data/season-videos.toml (facade, loads YouTube on click)."""
    vids = SEASON_VIDEOS.get(sid, [])
    if not vids:
        return ""
    many = len(vids) > 1
    return f'<div class="season-vids{" many" if many else ""}">' + "".join(
        f'<div class="video-facade single" data-ytv="{v["id"]}"><img class="vf-img" src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="" loading="lazy">'
        f'<button type="button" class="vf-play"><span aria-hidden="true">▶</span> {label} highlights'
        + (f' · part {v["part"]}' if v["part"] and many else "") + "</button></div>" for v in vids) + "</div>"


def honor_cards(R, y):
    """That year's names from the Hall lists, one card per list."""
    cards = []
    st = [r for r in HALL["state"] if int(r["year"]) == y]
    if st:
        cards.append(("PIAA champions", [f'<a href="{R}champions/{slug(r["wrestler"])}/">{e(r["wrestler"])}</a><span>{e(r["weight"])}</span>' for r in st]))
    md = sorted((r for r in HALL["medals"] if int(r["year"]) == y), key=lambda r: int(r["place"]))
    if md:
        cards.append(("State medalists", [f'{e(r["wrestler"])}<span>{PLACE[r["place"]]} · {e(r["weight"])}</span>' for r in md]))
    for k, lab in (("regional", "Northeast Regional champions"), ("district", "District XI champions")):
        rows = [r for r in HALL[k] if int(r["year"]) == y]
        if rows:
            cards.append((lab, [f'{e(r["wrestler"])}<span>{e(r["weight"])}</span>' for r in rows]))
    return "".join(f'<div class="hon-card"><h3>{t}</h3><ul role="list">' + "".join(f"<li>{x}</li>" for x in items) + "</ul></div>" for t, items in cards)


def hall_postseason(y):
    """Postseason rows (wrestler, weight, district, regional, PIAA) from the Hall lists for one year."""
    rows = {}
    def row(r):
        return rows.setdefault(norm(r["wrestler"]), [r["wrestler"], r["weight"].replace(" lbs", ""), "", "", ""])
    for r in HALL["district"]:
        if int(r["year"]) == y: row(r)[2] = "1st"
    for r in HALL["regional"]:
        if int(r["year"]) == y: row(r)[3] = "1st"
    for r in HALL["state"]:
        if int(r["year"]) == y: row(r)[4] = "Champion"
    for r in HALL["medals"]:
        if int(r["year"]) == y: row(r)[4] = PLACE[r["place"]]
    rank = lambda v: 0 if v == "Champion" else (int(v[0]) if v[:1].isdigit() else 9)
    return sorted(rows.values(), key=lambda x: (rank(x[4]), rank(x[3]), rank(x[2]), int(re.sub(r"\D", "", x[1]) or 0)))


def build_season_page(i, all_s):
    """One season, laid out the same way for every year (the layout the 2021-22+ seasons were built with)."""
    sid, label, y, pw, d = all_s[i]
    R = "../../"
    d = d or {}
    facts = season_facts(sid, y, pw, d or None)
    coach = season_coach(y)
    headline = d.get("headline") or " · ".join(season_phrases(facts, y in TITLE_YEARS))
    parts = []
    if sid == CUR["id"]:
        parts.append(f'<div class="prose"><p>{d["dual_record"]} in duals, Parkland Duals champions, and 3rd at the District XI, Northeast Regional, and PIAA tournaments. Brayden Wenrich (114) and Gabe Ballard (152) won state titles, and Trey Wagner won a regional title at 139.</p>'
                     f'<p><a class="btn" href="{R}high-school/">Full 2025–26 recap</a></p></div>')
    if d.get("summary"):
        parts.append('<div class="prose cols">' + "".join(f"<p>{e(x)}</p>" for x in d["summary"]) + "</div>")
    # Team results list
    if d.get("team_finishes"):
        res = [("Dual meet record", d["dual_record"])] + [tuple(x) for x in d["team_finishes"]]
    else:
        res = ([("Dual meet record", pw["record"] + (f' ({pw["league_record"]} league)' if pw["league_record"] else ""))] if pw["record"] else [])
        res += [tuple(x) for x in pw["finishes"]] + [tuple(x) for x in pw["tournaments"]]
    who = d.get("coaches") or (f"Head coach: {coach}" if coach else "")
    left = (f'<h2 class="sub">Team results</h2><ul class="results" role="list">{result_rows(res)}</ul>' if res else '<h2 class="sub">Team results</h2><p class="arch-none">No stats available.</p>')
    left += f'<p class="season-coaches">{e(who)}</p>' if who else ""
    if y in TITLE_YEARS:
        left += f'<p><a class="text-link" href="{R}champions/team/{y}/">The {label} PIAA team title season ›</a></p>'
    right = figure(R, d["team_photo"], "(min-width: 900px) 40vw, 100vw", "wide-fig") if d.get("team_photo") else ""
    if not right and pw["duals"]:
        right = ('<h2 class="sub">Duals</h2><ul class="arch-duals" role="list">' + "".join(
            f'<li><span class="ad-date">{e(x["date"])}</span><span class="ad-opp">{e(x["opponent"])}'
            + (f' <small>{e(x["event"])}</small>' if x["event"] else "") + (' <small>league</small>' if x["league"] else "")
            + f'</span><b class="nw">{e(x["result"])}</b></li>' for x in pw["duals"]) + '</ul><p class="fine">Winner’s score first.</p>')
        pw_duals_shown = True
    else:
        pw_duals_shown = False
    parts.append(f'<div class="split narrow-right top">' + f"<div>{left}</div>" + (f"<div>{right}</div>" if right else "") + "</div>")
    if d.get("portraits"):
        parts.append('<div class="portraits">' + "".join(
            f'<article class="medalist">{picture(R, pid, "(min-width: 900px) 15vw, 45vw")}<h3>{e(n)}</h3><p>{e(l)}</p></article>'
            for pid, n, l in d["portraits"]) + "</div>")
    post = d.get("postseason") or hall_postseason(y)
    aw = ""
    if d.get("awards"):
        aw += f'<h2 class="sub">Season awards</h2><dl class="awards compact">{"".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in d["awards"])}</dl>'
    if d.get("leaders"):
        aw += f'<h2 class="sub">Team leaders</h2><dl class="awards compact">{"".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in d["leaders"])}</dl>'
    if post or aw:
        tbl = f'<h2 class="sub">Postseason</h2>{postseason_table(post, label + " postseason results by wrestler")}' if post else ""
        parts.append(f'<div class="split even top"><div>{tbl}</div><div>{aw}</div></div>' if aw else f'<div class="top-gap">{tbl}</div>')
    extra = []
    if d.get("epc"):
        extra.append(f'<div><h2 class="sub">EPC all-stars</h2><ul class="results" role="list">{result_rows(d["epc"])}</ul></div>')
    if d.get("jv"):
        extra.append(f'<div><h2 class="sub">{d["jv_title"]}</h2><ul class="results" role="list">{result_rows(d["jv"])}</ul></div>')
    honors = []
    if d.get("never_pinned"):
        honors.append(f'<h2 class="sub">Never pinned</h2><p>{e(", ".join(d["never_pinned"]))}</p>')
    if d.get("forty_point"):
        honors.append('<h2 class="sub">“40” Point Club</h2><p>' + "<br>".join(f"<b>{e(a)}:</b> {e(b)}" for a, b in d["forty_point"]) + "</p>")
    if d.get("lerch"):
        honors.append(f'<h2 class="sub">Charlie Lerch Memorial Scholarships</h2><p>{e(", ".join(d["lerch"]))}</p>')
    if honors:
        extra.append('<div class="prose">' + "".join(honors) + "</div>")
    tail = ""
    if d.get("seniors"):
        tail += '<h2 class="sub">Seniors</h2><p>' + "<br>".join(f"<b>{e(r[0])}</b>" + (f" — {e(r[2])}" if r[2] else "") for r in d["seniors"]) + "</p>"
    elif d.get("seniors_list"):
        tail += f'<h2 class="sub">Seniors</h2><p>{e(d["seniors_list"])}</p>'
    jh = d.get("junior_high")
    if isinstance(jh, dict):
        bits = [f'{jh["record"]} in duals'] + [f"{a}: {b}" for a, b in jh.get("finishes", [])]
        pwn = ", ".join(f"{n} ({pl})" for n, pl in jh.get("placewinners", []))
        tail += f'<h2 class="sub">Junior high</h2><p>{e(". ".join(bits))}.' + (f" District placewinners: {e(pwn)}." if pwn else "") + "</p>"
    elif jh:
        tail += f'<h2 class="sub">Junior high</h2><p>{e(jh)}</p>'
    if tail:
        extra.append(f'<div class="prose">{tail}</div>')
    if extra:
        parts.append(f'<div class="trio-text">{"".join(extra)}</div>')
    if d.get("roster"):
        parts.append('<details class="season-roster"><summary>Full ' + e(label) + ' roster</summary><dl class="awards compact">'
                     + "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in d["roster"]) + "</dl></details>")
    if pw["duals"] and not pw_duals_shown:
        parts.append('<details class="season-roster"><summary>All ' + e(label) + ' duals</summary><ul class="arch-duals" role="list">' + "".join(
            f'<li><span class="ad-date">{e(x["date"])}</span><span class="ad-opp">{e(x["opponent"])}'
            + (f' <small>{e(x["event"])}</small>' if x["event"] else "") + (' <small>league</small>' if x["league"] else "")
            + f'</span><b class="nw">{e(x["result"])}</b></li>' for x in pw["duals"]) + '</ul><p class="fine">Winner’s score first.</p></details>')
    sv = season_videos(sid, label)
    if sv:
        parts.append(f'<h2 class="sub">Season highlight video{"s" if len(SEASON_VIDEOS[sid]) > 1 else ""}</h2>{sv}')
    if d.get("gallery"):
        parts.append(f'<h2 class="sub">Photos</h2>{gallery(R, d["gallery"], "season-" + sid)}')

    newer = all_s[i - 1] if i > 0 else None
    older = all_s[i + 1] if i + 1 < len(all_s) else None
    nav = ('<nav class="season-nav" aria-label="More seasons">'
           + (f'<a href="../{older[0]}/">‹ {older[1]}</a>' if older else "<span></span>")
           + '<a href="../">All seasons</a>'
           + (f'<a href="../{newer[0]}/">{newer[1]} ›</a>' if newer else "<span></span>") + "</nav>")
    body = (f'<section class="band season season-page" id="{sid}" aria-labelledby="h-{sid}"><div class="wrap">'
            f'<p class="kicker"><a href="../">‹ All seasons</a></p>'
            + section_head(f'<span id="h-{sid}">{label}</span>', e(headline), level=1)
            + "".join(parts) + nav + "</div></section>")
    desc = f"Northampton wrestling {label} season" + (f": {headline}." if headline else ".")
    return page(f"seasons/{sid}/index.html", f"{label} Season", desc, body, "seasons/", og_image=d.get("team_photo") or "team-2025")


def build_seasons():
    R = "../"
    all_s = season_list()
    urls = [build_season_page(i, all_s) for i in range(len(all_s))]
    dec = {}
    for sid, label, y, pw, d in all_s:
        facts = season_facts(sid, y, pw, d)
        title = y in TITLE_YEARS
        rec = [b_ for a_, b_ in facts if a_ == "Dual record"]
        chips = (f"<li>Dual record: <b>{e(rec[0])}</b></li>" if rec else "") + "".join(
            f"<li>{e(x)}</li>" for x in season_phrases(facts, title) if not (title and x == "PIAA team champions"))
        thumb = picture(R, d["team_photo"], "(min-width: 900px) 25vw, 90vw", "sc-img", alt="") if d and d.get("team_photo") else ""
        card = (f'<a class="sc{" title" if title else ""}{" has-img" if thumb else ""}" href="{sid}/" id="{sid}">{thumb}<span class="sc-body">'
                f'<span class="sc-yr">{label}</span>'
                + ('<span class="sc-badge">PIAA team champions</span>' if title else "")
                + (f'<span class="sc-head">{e(d["headline"])}</span>' if d else "")
                + (f'<ul class="sc-facts" role="list">{chips}</ul>' if chips else "")
                + ('<span class="sc-vid">▶ Highlight video</span>' if SEASON_VIDEOS.get(sid) else "")
                + "</span></a>")
        dec.setdefault(y - 1 - (y - 1) % 10, []).append(card)
    order = sorted(dec, reverse=True)
    jump = "".join(f'<a href="#d{d}s">{d}<span class="lc">s</span></a>' for d in order)
    groups = "".join(f'<section class="band season-dec" aria-labelledby="d{d}s"><div class="wrap"><h2 id="d{d}s">{d}<span class="lc">s</span></h2>'
                     f'<div class="sc-grid">{"".join(dec[d])}</div></div></section>' for d in order)
    redirect_js = ('<script>(function(){var m=location.hash.match(/^#(?:season-)?(\\d{4}-\\d{2})$/);'
                   'if(m)location.replace(m[1]+"/");})();</script>')
    body = f"""
{page_head(R, "Past Seasons", "Every Konkrete Kids season since 1946–47. Pick a season for its results, champions, duals, and video.")}
<nav class="jump seasons-jump wrap" aria-label="Decades"><div class="jump-row">{jump}</div></nav>
{groups}
{redirect_js}
"""
    page("seasons/index.html", "Past Seasons", "Northampton wrestling season archive: results, state medalists, and awards for every season.", body, "seasons/", og_image="team-2025")
    return [SITE["domain"] + "/seasons/"] + [SITE["domain"] + f"/seasons/{x[0]}/" for x in all_s]


def build_404():
    body = """
<header class="page-head concrete"><div class="wrap"><h1>Page not found</h1>
<p class="lede">That page moved when the site was rebuilt, or the address has a typo.</p>
<p class="actions"><a class="btn" href="/">Go to the home page</a><a class="btn ghost" href="/champions/">Hall of Champions</a></p></div></header>
"""
    # 404 is served from any depth, so it uses root-relative links (correct once the custom domain is live)
    out = page("404.html", "Page not found", "Page not found.", body)
    p = os.path.join(ROOT, "404.html")
    s = open(p).read().replace('href="assets/', 'href="/assets/').replace('src="assets/', 'src="/assets/') \
        .replace('href="site.webmanifest"', 'href="/site.webmanifest"').replace('<a class="brand" href="./"', '<a class="brand" href="/"')
    s = re.sub(r'href="((?:high-school|schedule|junior-high|youth|coaching-staff|champions|seasons|story|facilities|roster|results|timeline|news|photos|videos|follow|family|alumni|join)/[^"]*)"', r'href="/\1"', s)
    s = re.sub(r'(?<=[" ,])assets/', '/assets/', s).replace('//assets/', '/assets/')
    s = s.replace('<li><a href="">Home</a></li>', '<li><a href="/">Home</a></li>')
    open(p, "w").write(s)
    return None


def redirect(path, target):
    depth = path.count("/")
    R = "../" * depth
    dest = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved</title>
<link rel="canonical" href="{SITE['domain']}/{target}"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={R}{target}"></head>
<body><p>This page moved to <a href="{R}{target}">{SITE['domain']}/{target}</a>.</p></body></html>
""")


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import v2
    v2.M = sys.modules[__name__]
    urls = [v2.build_home(), build_high_school(), build_schedule(), build_junior_high(), build_youth(),
            build_coaches(), build_champions()] + build_seasons()
    urls += v2.build_all(sys.modules[__name__])
    build_404()
    # Old Wix addresses keep working
    redirect("schedule-1/index.html", "schedule/")
    redirect("copy-of-high-school/index.html", "seasons/2022-23/")
    redirect("copy-of-high-school-1/index.html", "seasons/2023-24/")
    redirect("coaches/index.html", "coaching-staff/")
    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE['domain']}/sitemap.xml\n")
    print(f"built {len(urls)} pages")


if __name__ == "__main__":
    main()
