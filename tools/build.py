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
# Youth Coaches' Playbook on/off (paused Oct. 2026; see youth_coaches_page in data/site.toml)
YOUTH_COACHES_LIVE = bool(SITE.get("youth_coaches_page", False))
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
try:
    import tomllib as _tl
    TEAM_PHOTOS = {k: v.get("team_photo") for k, v in _tl.load(open(os.path.join(ROOT, "data/hall/team-seasons.toml"), "rb")).items() if isinstance(v, dict) and v.get("team_photo")}
except Exception:
    TEAM_PHOTOS = {}

SEASON_VIDEOS = load_toml("season-videos.toml")
CUR = SEASONS[0]

NAV_GROUPS = [
    ("Program", [("story/", "Our Story"), ("coaching-staff/", "Coaches"), ("facilities/", "Our Home"),
                 ("high-school/", "Varsity"), ("junior-high/", "Junior High"), ("youth/", "Youth")]
                + ([("youth/coaches/", "Youth Coaches")] if YOUTH_COACHES_LIVE else [])),
    ("Team", [("roster/", "Roster"), ("schedule/", "Schedule"), ("results/", "Results"), ("high-school/#stats-title", "Stats")]),
    ("Tradition", [("champions/", "Hall of Champions"), ("champions/#team-title", "Team Titles"),
                   ("champions/#hundred-title", "100-Win Club"), ("champions/#lists-title", "Record Book"),
                   ("timeline/", "Timeline"), ("seasons/", "Past Seasons"), ("trivia/", "Trivia")]),
    ("Media", [("news/", "News"), ("videos/", "Videos"), ("follow/", "Follow & Email List")]),
    ("Parents", [("family/", "Parent Information"), ("youth/#pt-title", "Youth Parent Guide"), ("family/#faq", "FAQs"), ("family/#booster", "Booster Club")]),
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
      <p><a href="{SITE['links']['share_form']}" rel="noopener" target="_blank">Share photos &amp; video</a></p>
      <p>{SITE['phone_label']}: <a href="tel:+1{SITE['phone'].replace('-', '')}">{SITE['phone']}</a></p>
      <p>{SITE['school']}<br>{'<br>'.join(SITE['address'])}</p>
    </div>
    <div>
      <h2>Explore</h2>
      <ul role="list" class="foot-links">{''.join(f'<li><a href="{R}{items[0][0]}">{g}</a></li>' for g, items in NAV_GROUPS)}<li><a href="{R}follow/">Follow</a></li></ul>
    </div>
  </div>
  <div class="wrap foot-base">
    <div>
      <p>&copy; <span data-year>2026</span> {SITE['owner']}</p>
      <p>*The Northampton Area School District does not sponsor or sanction this program/event/activity.</p>
    </div>
    <p class="foot-note">Parents: to have a photo or your wrestler’s name removed, email <a href="mailto:{SITE['email']}?subject=Photo%20removal%20request">{SITE['email']}</a>.</p>
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


def page_head(R, title, intro, photo=None, focus=None, kicker=None, cls=""):
    k = f'<p class="kicker">{kicker}</p>' if kicker else ""
    if photo:
        return (f'<header class="page-head has-photo{(" " + cls) if cls else ""}">{picture(R, photo, "100vw", "bg", True, alt="", focus=focus)}'
                f'<div class="wrap">{k}<h1>{title}</h1><p class="lede">{intro}</p></div>'
                + (f'<p class="ph-credit">Photo: {e(PHOTOS[photo]["credit"])}</p>' if PHOTOS[photo].get("credit") else "") + '</header>')
    return f'<header class="page-head concrete"><div class="wrap">{k}<h1>{title}</h1><p class="lede">{intro}</p></div></header>'


def hall_wall_head(R, title, intro):
    """Hall of Champions header: a wall of every state champion's banner photo, oldest first
    (Joe, Oct. 21, 2026). Uses the same photo as each champion's banner (headshot first)."""
    names = []
    for r in load_csv("hall/state-champions.csv"):
        if r["wrestler"] not in names:
            names.append(r["wrestler"])
    tiles = []
    for n in names:
        c = CHAMPS.get(n, {})
        bid = c.get("headshot") or c.get("banner")
        if bid:
            tiles.append(f'<span class="hw-tile">{picture(R, bid, "(min-width: 900px) 10vw, 20vw", alt="")}</span>')
    return (f'<header class="page-head has-photo hall-wall"><div class="hw-grid" aria-hidden="true">{"".join(tiles)}</div>'
            f'<div class="wrap"><h1>{title}</h1><p class="lede">{intro}</p></div></header>')


def result_rows(rows):
    return "".join(f"<li><span>{e(a)}</span><b>{e(b)}</b></li>" for a, b in rows)


def place_cell(v, blank=False):
    if not v:
        return '<td class="na"></td>' if blank else '<td class="na">—</td>'
    cls = "gold" if v in ("Champion", "1st") else ("podium" if v in ("2nd", "3rd") else "")
    return f'<td class="{cls}">{e(v)}</td>'


def postseason_table(rows, caption, titles_only=False):
    body = "".join(
        f"<tr><th scope=\"row\">{e(n)}{f' <span class=\"wt\">{w}</span>' if w else ''}</th>{place_cell(d, titles_only)}{place_cell(r, titles_only)}{place_cell(s, titles_only)}</tr>"
        for n, w, d, r, s in rows)
    return (f'<div class="table-wrap" tabindex="0" role="region" aria-label="{e(caption)}"><table class="path"><caption>{caption}</caption>'
            f'<thead><tr><th scope="col">Wrestler</th><th scope="col">District XI</th><th scope="col">NE Regional</th><th scope="col">PIAA</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>'
            + ('<p class="fine">District XI and NE Regional columns list titles; the PIAA column lists state medals.</p>' if titles_only else ""))


CHAMPS = load_toml("hall/champions.toml")


def pennant(year, name, weight, small=False, R=None):
    """A state-champion banner. With R (path prefix) it links to the champion's page
    and shows the banner headshot when one is set in data/hall/champions.toml."""
    if R is None:
        return (f'<li class="pennant{" sm" if small else ""}"><span class="yr">{year}</span>'
                f'<span class="nm">{e(name)}</span><span class="wt">{e(weight)}</span></li>')
    c = CHAMPS.get(name, {})
    bid = c.get("headshot") or c.get("banners", {}).get(str(year)) or c.get("banner")
    if bid:
        face = picture(R, bid, "160px", "pn-face", alt="")
    else:
        face = f'<span class="pn-face pn-logo"><img src="{R}assets/img/logo-96.png" alt="" width="56" height="48" loading="lazy"></span>'
    return (f'<li class="pennant linked{" has-face" if (c.get("headshot") or c.get("banner")) else ""}{" headshot" if c.get("headshot") else ""}"><a href="{R}champions/{slug(name)}/">'
            f'<span class="yr">{year}</span>{face}<span class="nm">{e(name)}</span><span class="wt">{e(weight)}</span>'
            f'<span class="pn-cta" aria-hidden="true">{"▶ Story &amp; video" if c.get("video") else "Read the story"}</span>'
            f'<span class="visually-hidden">: read the story{" and watch the video" if c.get("video") else ""}</span></a></li>')


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
    for title, ctr in (("State Medalists", medals), ("Regional Champions", c["regional"]),
                       ("District XI Champions", c["district"])):
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


# Other names people search for in the Hall finder (nicknames, names used in stories and on the roster)
SEARCH_ALIASES = {"Gabriel Ballard": ["Gabe Ballard"], "Edward Keglovits": ["Ed Keglovits"], "Dennis Liberto": ["Denny Liberto"],
           "Whitey Chlebove": ["Ian Chlebove"]}


def hall_json():
    people = defaultdict(lambda: {"honors": []})
    for k, label in (("state", "PIAA Champion"), ("regional", "Northeast Regional Champion"), ("district", "District XI Champion")):
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
        out.append({"name": n, "honors": d["honors"], **({"aka": SEARCH_ALIASES[n]} if n in SEARCH_ALIASES else {})})
    out.sort(key=lambda p: p["name"].split()[-1] + p["name"])
    return out


# ------------------------------------------------------------------ pages
def build_home():
    R = ""
    s = CUR
    wins = {r["wrestler"]: r for r in STATS}
    champ = lambda pid, name, wt, lines: (
        f'<article class="champ-card">{picture(R, pid, "(min-width: 900px) 40vw, 90vw")}'
        f'<div class="champ-body"><p class="champ-tag">PIAA Champion at {wt} pounds</p><h3>{name}</h3>'
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
    <p><b>2</b> State Champions</p>
    <p><b>3</b> Northeast Regional Champions</p>
    <p><b>5</b> state qualifiers</p>
  </div>
</section>

<section class="band dark champs" aria-labelledby="champs-title">
  <div class="wrap">
    {section_head('<span id="champs-title">Two State Champions</span>', 'Brayden Wenrich and Gabe Ballard won PIAA titles in Hershey in March 2026, the first time since 2004 that Northampton crowned two State Champions in the same year.')}
    <div class="champ-grid">
      {champ("portrait-wenrich-2026", "Brayden Wenrich", "114", [f"{w['wins']}–{w['losses']} as a sophomore", "District XI, Northeast Regional, and PIAA Champion", "Fastest pin of the season: 9 seconds", f"{w['career_wins']}–{w['career_losses']} career record"])}
      {champ("portrait-ballard-2026", "Gabe Ballard", "152", [f"{b['wins']}–{b['losses']} as a junior", "District XI, Northeast Regional, and PIAA Champion", "114 takedowns, 238 team points", f"{b['career_wins']} career wins"])}
    </div>
    <div class="also">
      <article class="mini">{picture(R, "portrait-wagner-2026", "160px")}<div><h3>Trey Wagner</h3><p>Northeast Regional Champion and state 7th at 139. Finished his career {t['career_wins']}–{t['career_losses']}.</p></div></article>
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
      <p>Our mission is to give young people a supportive, demanding place to grow as wrestlers and as responsible, resilient, respectful members of the community.</p>
      <p><a class="text-link" href="coaching-staff/">Meet the coaching staff</a></p>
    </div>
    {figure(R, "program-family", "(min-width: 1180px) 1100px, 100vw", "natural-fig program-fig")}
  </div>
</section>

<section class="band concrete" aria-labelledby="wall-title">
  <div class="wrap">
    {section_head('<span id="wall-title">The banner wall</span>', f'{TOTALS["state"]} PIAA State Champions since 1955. These are the last ten.')}
    <p class="wall-hint"><span aria-hidden="true">▶</span> Tap a banner for the champion’s story. ▶ means there’s state-final video.</p>
    <ol class="pennants" role="list" reversed>{''.join(pennant(r['year'], norm(r['wrestler']), r['weight'], R=R) for r in recent[:10])}</ol>
    <div class="numbers">
      <p><b>{TOTALS['team_titles']}</b> PIAA team titles</p>
      <p><b>{TOTALS['state']}</b> individual state titles</p>
      <p><b>{TOTALS['medals']}</b> State Placewinners</p>
      <p><b>{TOTALS['regional']}</b> Northeast Regional Champions</p>
      <p><b>{TOTALS['district']}</b> District XI Champions</p>
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
      <a class="level" href="junior-high/">{picture(R, "jh-districts", "(min-width: 900px) 33vw, 100vw")}<span><b>Junior high</b>Grades 7–9, the bridge to the varsity room</span></a>
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
    evs = sorted(load_results().get("event", []), key=lambda x: x["date"])
    opener = (f'The 2026–27 season opens {evs[0]["date"]:%B %-d} {"against" if evs[0].get("home") else "at"} {e(evs[0]["opponent"])}.'
              if evs else "The new season starts this winter.")
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
    stats_table = (f'<div class="table-wrap" tabindex="0"><table class="sortable stats"><caption>2025–26 varsity final stats. Select a column heading to sort. Highlighted numbers led the team.</caption>'
                   f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody>'
                   f'<tfoot><tr><th scope="row">Team</th><td>{tw}–{tl}</td><td>{tot("falls")}</td><td>{tot("tech_falls")}</td><td>{tot("major_decisions")}</td><td>{tot("takedowns")}</td><td>{tot("team_points_duals")}</td><td></td></tr></tfoot></table></div>')

    seniors = "".join(
        f'<li><h3>{e(n)}</h3><p class="wt">{w} lbs</p><p class="next">Next: {e(nx)}</p>'
        + (f'<blockquote><p>“{e(q)}”</p><footer>A coaching line he won’t forget</footer></blockquote>' if q else "") + "</li>"
        for n, w, nx, q in s["seniors"])
    awards = "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in s["awards"])
    medal_card = lambda pid, name, line: (f'<article class="medalist">{picture(R, pid, "(min-width: 900px) 18vw, 45vw")}'
                                         f'<h3>{name}</h3><p>{line}</p></article>')
    body = f"""
{page_head(R, "High School", "Northampton Area High School boys wrestling: varsity and JV.", "dark-stance", "50% 55%")}

<section class="band" aria-labelledby="now-title">
  <div class="wrap split narrow-right">
    <div class="prose">
      <h2 id="now-title">2026–27</h2>
      <p>{opener} Lineups and results will be added during the season.</p>
      <p>Both of last season’s State Champions are back: Brayden Wenrich is now a junior and Gabe Ballard a senior.</p>
      <p class="actions"><a class="btn" href="../schedule/">Schedule</a><a class="btn ghost dark-ink" href="../coaching-staff/">Coaching staff</a></p>
    </div>
  </div>
  <div class="wrap">{figure(R, "team-mayhem", "(min-width: 1180px) 1100px, 100vw", "natural-fig program-fig")}</div>
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
      {medal_card("portrait-wenrich-2026", "Brayden Wenrich", "PIAA Champion, 114")}
      {medal_card("portrait-ballard-2026", "Gabe Ballard", "PIAA Champion, 152")}
      {medal_card("portrait-wagner-2026", "Trey Wagner", "Regional Champion, PIAA 7th, 139")}
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
      <details><summary>Chris Gmitter Picture Plaque Awards</summary><p>Regional qualifiers receive a plaque. District Champions, Regional Champions, and state qualifiers receive a picture plaque, and district, regional, and State Placewinners have their names added to the plaques in the wrestling room.</p></details>
      <details><summary>Charlie Lerch Memorial Scholarship</summary><p>Awarded to graduating seniors who wrestled in the Northampton program for at least three seasons, including senior year, and who enroll in higher education.</p></details>
      <details><summary>Brandon M. Sommer Memorial Scholarship</summary><p>A $500 award to the senior, a three-year member of the team, with the highest combined score for GPA and District, Regional, and State placement.</p></details>
      <p><a class="text-link" href="../seasons/">Earlier seasons</a></p>
    </div>
  </div>
</section>
"""
    return page("high-school/index.html", "High School", "Northampton High School wrestling: 2025–26 results, State Champions, final stats, awards, and the Class of 2026.", body, "high-school/", og_image="team-mayhem")



def load_results():
    with open(os.path.join(ROOT, "data", "results.toml"), "rb") as f:
        return tomllib.load(f)


def event_title(ev):
    """'vs. Easton' / 'at Whitehall' for duals; tournaments go by their name."""
    if ev.get("kind", "dual") == "tournament":
        return ev["opponent"]
    return ("vs. " if ev.get("home") else "at ") + ev["opponent"]


def event_where(ev, full=False):
    """Home matches: the gym (full=True adds school and street for map apps). Otherwise the event's location."""
    if ev.get("home") and not ev.get("location"):
        return f'{SITE["gym"]}, {SITE["school"]}, {", ".join(SITE["address"])}' if full else SITE["gym"]
    return ev.get("location", "")


def event_days(ev):
    """('Dec 11–12', 'Fri–Sat') for the schedule list."""
    d, end = ev["date"], ev.get("end_date")
    if not end or end == d:
        return d.strftime("%b %-d"), d.strftime("%a")
    if end.month == d.month:
        return f"{d:%b %-d}–{end.day}", f"{d:%a}–{end:%a}"
    return f"{d:%b %-d}–{end:%b %-d}", f"{d:%a}–{end:%a}"


def event_long_date(ev):
    """'Wednesday, December 9' or 'Fri–Sat, December 11–12' for the home page."""
    d, end = ev["date"], ev.get("end_date")
    if not end or end == d:
        return d.strftime("%A, %B %-d")
    if end.month == d.month:
        return f"{d:%a}–{end:%a}, {d:%B %-d}–{end.day}"
    return f"{d:%B %-d}–{end:%B %-d}"


def cal_base():
    """Where schedule.ics can be fetched today. GitHub writes a CNAME file into the repo once the custom
    domain is set up; until then use the github.io address (GitHub redirects it to the domain afterward,
    so early subscribers keep getting updates)."""
    return SITE["domain"] if os.path.exists(os.path.join(ROOT, "CNAME")) else SITE["test_url"]


ICS_TZ = ["BEGIN:VTIMEZONE", "TZID:America/New_York",
          "BEGIN:DAYLIGHT", "TZOFFSETFROM:-0500", "TZOFFSETTO:-0400", "TZNAME:EDT", "DTSTART:19700308T020000",
          "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", "END:DAYLIGHT",
          "BEGIN:STANDARD", "TZOFFSETFROM:-0400", "TZOFFSETTO:-0500", "TZNAME:EST", "DTSTART:19701101T020000",
          "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", "END:STANDARD", "END:VTIMEZONE"]


def ics_fold(line):
    """Calendar files wrap lines longer than 75 bytes; each continuation starts with a space."""
    parts, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (74 if parts else 75):
            parts.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def build_calendar():
    """schedule.ics from data/results.toml events, so parents can subscribe once and get every match.
    Duals with a time are timed events; tournaments and anything without a time are all-day events
    (a tournament's start time goes in the notes). Returns the events, oldest first."""
    import datetime as _dt
    evs = sorted(load_results().get("event", []), key=lambda x: x["date"])
    def esc(t):
        return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Northampton Wrestling//Schedule//EN", "CALSCALE:GREGORIAN",
           "METHOD:PUBLISH", "X-WR-CALNAME:Northampton Wrestling", "X-WR-TIMEZONE:America/New_York",
           "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"] + (ICS_TZ if evs else [])
    stamp = "20260101T000000Z"  # fixed so rebuilding does not change the file
    page_url = cal_base() + "/schedule/"
    for ev in evs:
        d = ev["date"]
        name = ev.get("opponent", "Match")
        tourney = ev.get("kind", "dual") == "tournament"
        t = ev.get("time", "").strip()
        notes = []
        lines = ["BEGIN:VEVENT", f"UID:{d.isoformat()}-{slug(name)}@northamptonwrestling.org", f"DTSTAMP:{stamp}",
                 "SUMMARY:" + esc(("Wrestling: " + name) if tourney else ("Wrestling " + event_title(ev)))]
        start = None
        if t and not tourney:
            try:
                start = _dt.datetime.combine(d, _dt.datetime.strptime(t.upper(), "%I:%M %p").time())
            except ValueError:
                start = None
        if start:
            end = start + _dt.timedelta(hours=2)
            lines += [f"DTSTART;TZID=America/New_York:{start:%Y%m%dT%H%M%S}", f"DTEND;TZID=America/New_York:{end:%Y%m%dT%H%M%S}"]
        else:
            end_d = ev.get("end_date", d) + _dt.timedelta(days=1)
            lines += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{end_d:%Y%m%d}", "TRANSP:TRANSPARENT"]
            notes.append(f"Starts {t}." if t else "Time to be announced.")
        if ev.get("league"):
            notes.append("League match.")
        if ev.get("postseason"):
            notes.append("Postseason.")
        if ev.get("result"):
            notes.append("Result: " + " ".join(x for x in [ev["result"], ev.get("score", "")] if x) + ".")
        notes.append(f"Times can change. Latest schedule: {page_url}")
        where = event_where(ev, full=True)
        if where:
            lines.append(f"LOCATION:{esc(where)}")
        lines += [f"DESCRIPTION:{esc(' '.join(notes))}", f"URL:{page_url}", "END:VEVENT"]
        out += lines
    out.append("END:VCALENDAR")
    with open(os.path.join(ROOT, "schedule.ics"), "w", newline="") as f:
        f.write("\r\n".join(ics_fold(x) for x in out) + "\r\n")
    return evs


def schedule_list(evs):
    """The season's events grouped by month: date, matchup, tags, place, and the time (or the result)."""
    import datetime as _dt
    months = {}
    for ev in evs:
        months.setdefault((ev["date"].year, ev["date"].month), []).append(ev)
    out = []
    for (y, m), items in months.items():
        rows = []
        for ev in items:
            day, dow = event_days(ev)
            tags = ([('home', 'Home')] if ev.get("home") else []) + ([('', 'League')] if ev.get("league") else []) \
                + ([('post', 'Postseason')] if ev.get("postseason") else []) \
                + ([('', 'Tournament')] if ev.get("kind") == "tournament" and not ev.get("postseason") else [])
            tag_html = "".join(f'<span class="ev-tag{" " + c if c else ""}">{lab}</span>' for c, lab in tags)
            if ev.get("result"):
                res = ev["result"] + (" " + ev["score"] if ev.get("score") else "")
                right = f'<b class="ev-res{" win" if ev["result"] == "W" else ""}">{e(res)}</b>'
            else:
                right = e(ev["time"]) if ev.get("time") else '<span class="ev-tba">TBA</span>'
            rows.append(f'<li class="ev-row{" is-home" if ev.get("home") else ""}">'
                        f'<time class="ev-date" datetime="{ev["date"].isoformat()}"><b>{day}</b><span>{dow}</span></time>'
                        f'<div class="ev-main"><p class="ev-title">{e(event_title(ev))}</p>'
                        f'<p class="ev-meta">{tag_html}<span>{e(event_where(ev))}</span></p></div>'
                        f'<p class="ev-time">{right}</p></li>')
        out.append(f'<h3 class="ev-month">{_dt.date(y, m, 1):%B %Y}</h3><ol class="ev-list" role="list">{"".join(rows)}</ol>')
    return "".join(out)


def build_schedule():
    R = "../"
    res = load_results()
    evs = build_calendar()
    webcal = "webcal://" + cal_base().split("://", 1)[1] + "/schedule.ics"
    cal = (f'''<aside class="note-card cal-card" id="add-calendar"><h3>Add the schedule to your phone</h3>
      <p>Subscribe once and the whole schedule, including any changes, shows up in your calendar automatically.</p>
      <p class="actions"><a class="btn" href="{webcal}">Subscribe (iPhone / Mac)</a>
      <a class="btn ghost dark-ink" href="https://calendar.google.com/calendar/r?cid={webcal}" rel="noopener">Google Calendar</a></p>
      <p class="fine"><a href="{R}schedule.ics" download>Download the calendar file</a></p></aside>''') if evs else ""
    official = (f'''<aside class="note-card"><h3>Official calendar</h3>
      <p>The district’s athletics calendar is the official source for every Northampton team, including JV and junior high, bus times, and changes.</p>
      <p class="actions"><a class="btn" href="{SITE['links']['district_calendar']}" rel="noopener">District athletics calendar</a><a class="btn ghost dark-ink" href="{SITE['links']['district_athletics']}" rel="noopener">Northampton athletics website</a></p></aside>''')
    path = '''<aside class="note-card">
      <h3>Postseason path</h3>
      <ol class="steps">
        <li><b>District XI AAA Championships</b><span>Top finishers advance</span></li>
        <li><b>PIAA Northeast Regional AAA</b><span>Top finishers advance</span></li>
        <li><b>PIAA Championships</b><span>Giant Center, Hershey</span></li>
      </ol>
    </aside>'''
    follow = f'''<h2>Follow along on match day</h2>
      <p>Follow the team’s social accounts for news and photos during the season.</p>
      <div class="social dark-ink">{social_links()}</div>'''
    if evs:
        main = f'''<div class="ev-wrap">
      <h2>{res["season"]} varsity schedule</h2>
      <p class="ev-note">Home matches are at {SITE["gym"]}. Dates and times can change, so check the <a href="{SITE['links']['district_calendar']}" rel="noopener">district athletics calendar</a> before you go. <a href="#add-calendar">Add every match to your phone</a>.</p>
      {schedule_list(evs)}
      <div class="prose ev-follow">{follow}</div>
    </div>'''
        side = f'<div class="ev-side">{cal}{official}{path}</div>'
        intro, desc = (f"Every {res['season']} varsity dual and tournament, with times and places, and a calendar you can add to your phone.",
                       f"{res['season']} Northampton wrestling schedule: every varsity dual and tournament, with times, locations, and a phone calendar.")
    else:
        main = f'''<div class="prose">
      <h2>{res["season"]} schedule</h2>
      <p>The season schedule will be posted here once it is final. Until then, the district’s athletics calendar is the official source for every Northampton team, including bus times and changes.</p>
      <p class="actions"><a class="btn" href="{SITE['links']['district_calendar']}" rel="noopener">District athletics calendar</a><a class="btn ghost dark-ink" href="{SITE['links']['district_athletics']}" rel="noopener">Northampton athletics website</a></p>
      {follow}
    </div>'''
        side = f"<div>{path}</div>"
        intro, desc = (f"Varsity, JV, and junior high match schedules for {res['season']}.",
                       f"{res['season']} Northampton wrestling schedules for varsity, JV, and junior high.")
    body = f"""
{page_head(R, "Schedule", intro)}
<section class="band">
  <div class="wrap split narrow-right ev-split">
    {main}
    {side}
  </div>
</section>
"""
    return page("schedule/index.html", "Schedule", desc, body, "schedule/")


def build_junior_high():
    R = "../"
    jh = CUR["junior_high"]
    staff = COACHES["junior_high"]["staff"]
    body = f"""
{page_head(R, "Junior High", "Grades 7–9 (9th graders can wrestle on the junior high or high school team). Where Konkrete Kids learn what the varsity room expects.", "jh-districts-tight", "50% 5%", cls="fit-photo wide")}
<section class="band">
  <div class="wrap split even">
    <div>
      <h2>2026–27 coaching staff</h2>
      <ul class="results" role="list">{result_rows(staff)}</ul>
      <p class="fine">Coaches Braden Turner and Justin Haupt are both former District XI and Northeast Regional Champions for Northampton.</p>
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
      <h2>2026 District XI Placewinners</h2>
      <ul class="results on-dark" role="list">{result_rows(jh['placewinners'])}</ul>
    </div>
    <div class="prose">
      <h2>Recent history</h2>
      <p>In 2023–24 the junior high went 13–1 and won the District XI Junior High Tournament team title under Coach Joe Tocci. Three of that team’s District Champions, Brayden Wenrich, Davi Glykas, and Carter Chlebove, were in the varsity lineup two seasons later, and Wenrich won a state title.</p>
    </div>
  </div>
</section>
"""
    return page("junior-high/index.html", "Junior High", "Northampton junior high wrestling: coaching staff, results, and District Placewinners.", body, "junior-high/", og_image="jh-districts")


def build_trivia():
    """Tradition > Trivia: rounds of multiple-choice questions from data/trivia.toml (assets/js/trivia.js runs them)."""
    R = "../"
    rounds = load_toml("trivia.toml")["round"]
    tabs = "".join(f'<button type="button" class="tv-tab" role="tab" id="tv-tab-{i}" aria-controls="tv-round-{i}" aria-selected="{str(i == 0).lower()}">{e(r["title"])}<span>{len(r["q"])} questions</span></button>'
                   for i, r in enumerate(rounds))
    secs = []
    for i, r in enumerate(rounds):
        qs = []
        for n, q in enumerate(r["q"], 1):
            assert len(q["choices"]) == 4 and 1 <= q["answer"] <= 4, q["q"]
            btns = "".join(f'<li><button type="button" class="tv-choice" data-i="{k}">{e(c)}</button></li>' for k, c in enumerate(q["choices"], 1))
            more = f' <a href="{R}{q["link"][1]}">{e(q["link"][0])} ›</a>' if q.get("link") else ""
            qs.append(f'<li class="tv-q" data-answer="{q["answer"]}"><p class="tv-num">Question {n} of {len(r["q"])}</p><h3>{e(q["q"])}</h3>'
                      f'<ol class="tv-choices" role="list">{btns}</ol>'
                      f'<div class="tv-reveal" hidden><p class="tv-verdict" aria-live="polite"></p><p class="tv-fact">{e(q["fact"])}{more}</p></div></li>')
        secs.append(f'<section class="tv-round" id="tv-round-{i}" role="tabpanel" aria-labelledby="tv-tab-{i}"{"" if i == 0 else " hidden"}>'
                    f'<p class="tv-blurb">{e(r["blurb"])}</p><ol class="tv-list" role="list">{"".join(qs)}</ol>'
                    f'<div class="tv-score" hidden><p class="tv-score-big"></p><p class="tv-score-line"></p>'
                    f'<p class="actions"><button type="button" class="btn tv-share">Share your score</button>'
                    f'<button type="button" class="btn ghost dark-ink tv-again">Try again</button>'
                    + (f'<button type="button" class="btn ghost dark-ink tv-next" data-next="{i + 1}">Next round: {e(rounds[i + 1]["title"])} ›</button>' if i + 1 < len(rounds) else "")
                    + '</p><p class="fine tv-copied" hidden>Copied. Paste it anywhere to challenge a friend.</p></div></section>')
    total = sum(len(r["q"]) for r in rounds)
    body = f"""
{page_head(R, "Konkrete Kids Trivia", f"{total} questions on the program’s champions, record holders, coaches, and biggest nights. How well do you know Northampton wrestling?")}
<section class="band tv">
  <div class="wrap tv-wrap">
    <div class="tv-tabs" role="tablist" aria-label="Trivia rounds">{tabs}</div>
    {"".join(secs)}
    <noscript><p class="fine">Turn on JavaScript to play.</p></noscript>
    <p class="fine tv-note">Know a great piece of Konkrete Kids trivia, or think we got one wrong? <a href="{SITE['links']['share_form']}" rel="noopener" target="_blank">Send it in</a>. We read everything but can’t reply individually.</p>
  </div>
</section>
"""
    return page("trivia/index.html", "Trivia", "Konkrete Kids trivia: test what you know about Northampton wrestling’s champions, records, coaches, and biggest team moments.",
                body, "trivia/", scripts=("site.js", "trivia.js"), og_image="team-mayhem")


def youth_model_html():
    """Black & Orange model (Joe's 'One Program. Two Strong Teams.' handout, Oct. 2026). Page 1 layout kept."""
    chk = '<svg class="ym-chk" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8.5l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    team = lambda cls, name: (f'<div class="ym-team {cls}"><h3>{name}</h3><ul role="list">'
        + "".join(f"<li>{chk}<span>{x}</span></li>" for x in ("Full varsity and JV lineups", "Its own coaching staff, year to year", "Built to stay together through 6th grade"))
        + "</ul></div>")
    means = [("A team they’re proud of.", "Our goal: no A team or B team, just two strong teams."),
             ("Meaningful matches.", "Two competitive teams mean close, real competition all season."),
             ("Coaches who know them.", "The same staff for years, watching them grow."),
             ("Teammates for the journey.", "Built to stay together from Novice to junior high.")]
    road = [("2026–27:", "a transition year. Some current wrestlers may move to help balance the rosters. Schedules are set by the previous year’s results and will even out as the teams balance."),
            ("Each fall:", "new Novice grads are placed to balance the teams."),
            ("Every season’s end:", "we review what worked and adjust."),
            ("In a few seasons:", "two equally strong teams.")]
    principles = [
        ("Develop for the long run, not early wins",
         [("“Focus on long-term learning over winning.”", "Its standard for ages 5–12.", "USA Wrestling · Athlete Development Model"),
          ("Youth program success", "“should not be measured by wins and losses alone.”", "National Wrestling Coaches Association")],
         "Kids grow on one team for years."),
        ("Don’t sort or label kids too early",
         [("Ended national titles", "for its youngest ages to stop “super teams” of 9- and 10-year-olds.", "USA Hockey"),
          ("Don’t cut kids.", "Add teams so more children play.", "Aspen Institute · Project Play")],
         "No A or B team. An even mix on each team, neither ranked above the other."),
        ("Keep young wrestlers off the scale",
         [("No weight loss for ages 5–12,", "other than for health reasons.", "USA Wrestling"),
          ("Rapid weight cutting", "is “potentially life threatening.”", "American Academy of Pediatrics")],
         "Team placement never depends on making weight."),
        ("Keep every kid in the sport",
         [("Its goal:", "“involving as many young people as possible.”", "NFHS"),
          ("Kids enjoy close competition", "more than blowouts, even when they lose.", "National Alliance for Youth Sports")],
         "Two competitive teams, so every kid has a real team and a reason to stay."),
    ]
    p_html = "".join(
        f'<div class="ym-pr"><h3><span class="ym-num">{i}</span>{t}</h3><div class="ym-quotes">'
        + "".join(f'<figure><blockquote><p><b>{a}</b> {b}</p></blockquote><figcaption>{s}</figcaption></figure>' for a, b, s in qs)
        + f'</div><p class="ym-in"><b>In our model ›</b> {m}</p></div>'
        for i, (t, qs, m) in enumerate(principles, 1))
    return f"""
<section class="ym-hero" aria-labelledby="ym-title">
  <div class="wrap">
    <p class="ym-kick">Northampton Youth Wrestling · Konkrete Kids · 2026–27</p>
    <h2 id="ym-title" class="ym-big">One program.<br><span>Two strong teams.</span></h2>
    <p class="ym-lede">Starting in 2026–27, we’re building Black and Orange as equals: balanced rosters, steady coaches, and a team for every wrestler from Novice to junior high.</p>
  </div>
</section>
<section class="band ym" aria-labelledby="ym-built">
  <div class="wrap ym-wrap">
    <p class="ym-label" id="ym-built">How the program is built</p>
    <div class="ym-flow">
      <div class="ym-pill ym-novice"><b>Novice</b> <span>Grades K–2 · fun and fundamentals</span></div>
      <div class="ym-split" aria-hidden="true"><span>Placed for an even mix</span></div>
      <div class="ym-teams">{team("black", "Northampton Black")}<span class="ym-eq" aria-label="equal to">=</span>{team("orange", "Northampton Orange")}</div>
      <div class="ym-room"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.1 0l3-3a5 5 0 0 0-7.1-7.1l-1.5 1.5M14 11a5 5 0 0 0-7.1 0l-3 3a5 5 0 0 0 7.1 7.1l1.5-1.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>
        <div><h3>Still one practice room</h3><p>Black and Orange varsity and JV keep holding joint practices. Day-to-day practice structure barely changes.</p></div></div>
      <div class="ym-stem" aria-hidden="true"></div>
      <div class="ym-pill ym-jh"><b>Junior high</b> <span>They move up together</span></div>
    </div>
    <div class="ym-means">
      <h3>What this means for your child</h3>
      <ul role="list">{"".join(f"<li>{chk}<span><b>{a}</b> {b}</span></li>" for a, b in means)}</ul>
    </div>
  </div>
</section>
<section class="band concrete ym" aria-labelledby="ym-why">
  <div class="wrap ym-wrap">
    <p class="ym-label">Why we’re doing this</p>
    <h2 id="ym-why">Every kid deserves a team they’re proud of.</h2>
    <div class="ym-stat"><b>70%</b><div><p class="ym-stat-h">of kids quit organized sports by age 13. The two biggest reasons:</p>
      <p class="ym-reasons"><span><em>1</em> It stopped being fun</span><span><em>2</em> “I’m not good enough”</span></p>
      <p class="ym-src">70%: American Academy of Pediatrics, 2024 · Reasons: youth-sports dropout surveys</p></div></div>
    <p class="ym-bar">Our model is built to guard against both.</p>
    <div class="ym-two">
      <div><h3><em>1</em> It stopped being fun</h3><div class="ym-change"><p class="ym-mini">How our model helps</p><p>Two competitive teams, so every kid gets meaningful matches.</p><p>Team placement is never decided on the scale.</p></div>
        <div class="ym-res"><p><b>Kids enjoy close competition</b> more than blowouts, even when they lose.</p><p class="ym-src">J. Engh, National Alliance for Youth Sports, 2019</p><p><b>No weight loss at ages 5–12</b> except for health reasons.</p><p class="ym-src">USA Wrestling, Athlete Development Model</p></div></div>
      <div><h3><em>2</em> “I’m not good enough”</h3><div class="ym-change"><p class="ym-mini">How our model helps</p><p>Our goal: no A team, no B team. Each team gets an even mix of experience levels.</p><p>Over time, two equally strong teams.</p></div>
        <div class="ym-res"><p><b>Sorted into A, B, and C teams,</b> 9- and 10-year-olds came to define themselves by their team.</p><p class="ym-src">Wrang et al., Sport, Exercise, and Performance Psychology, 2023</p><p><b>Don’t label young athletes:</b> “No child qualifies as elite before growing into their body.”</p><p class="ym-src">Aspen Institute Project Play</p></div></div>
    </div>
    <div class="ym-plus"><h3>Plus: steady coaches</h3><p>Each team keeps its coaches year to year, so coaches and wrestlers build real relationships over several seasons, and kids always know who’s in their corner.</p></div>
  </div>
</section>
<section class="band ym" aria-labelledby="ym-change">
  <div class="wrap ym-wrap">
    <p class="ym-label">Looking ahead</p>
    <h2 id="ym-change">The roadmap</h2>
    <div class="ym-two ym-gap">
      <div class="ym-move"><p class="ym-mini">When does a wrestler move?</p><p>Wrestlers usually stay put, but coaches can move a wrestler who’s stuck behind a teammate on JV. <b>For example:</b></p>
        <ol role="list"><li><span class="ym-tag">3rd gr</span><span>A wrestler is placed on <b>Orange</b>.</span></li><li><span class="ym-tag">5th gr</span><span>They improve a lot, but they’re the same weight as Orange’s varsity starter, so they’re stuck on JV.</span></li><li><span class="ym-tag dark">Move</span><span>Coaches move them to <b>Black</b> to wrestle varsity. Now both wrestlers are varsity starters.</span></li></ol>
        <p class="ym-src">Moves are the exception, made by coaches for the wrestler’s good.</p></div>
      <div class="ym-road"><p class="ym-mini">The roadmap</p><ol role="list">{"".join(f"<li><b>{a}</b> {b}</li>" for a, b in road)}</ol></div>
    </div>
  </div>
</section>
<section class="band concrete ym" aria-labelledby="ym-experts">
  <div class="wrap ym-wrap">
    <p class="ym-label">What the experts say</p>
    <h2 id="ym-experts">Built on the best advice in the sport.</h2>
    <p class="ym-lede-dark">Four principles behind our model, in the words of wrestling’s leaders and youth-sports researchers.</p>
    {p_html}
    <p class="ym-src ym-sources"><b>Sources:</b> American Academy of Pediatrics (2024; HealthyChildren.org) · USA Wrestling, Athlete Development Model · National Wrestling Coaches Association · youth-sports dropout surveys · NFHS · Aspen Institute Project Play · USA Hockey · Wrang et al. (2023) · J. Engh, National Alliance for Youth Sports (2019).</p>
  </div>
</section>
"""


PARENT_TEN = [
    ("Love them the same, win or lose.", "Say it before and after: “I love to watch you wrestle.”"),
    ("Be a great spectator.", "Coaches coach, referees ref, wrestlers wrestle. Parents cheer."),
    ("Cheer effort, not just results.", "A loss with real effort is a good day."),
    ("Make the car ride a safe place.", "Let them talk first, and leave the lessons to the coaches."),
    ("Keep it fun.", "Fun is the number one reason kids stay in wrestling."),
    ("Don’t compare.", "Every child grows on their own timeline."),
    ("No weight cutting.", "Youth wrestlers compete at their natural, healthy weight."),
    ("Honor the game.", "Respect referees, opponents, and coaches. Cheer for our team, not against theirs."),
    ("Healthy habits first.", "Good sleep, good food, schoolwork done, and clean gear."),
    ("Trust the coaches.", "Your encouragement and trust in the process make all the difference."),
]
PARENT_CLOSER = "Wrestling belongs to the kids. It’s their thing, not ours."
PARENT_SOURCES = "Built on guidance from USA Wrestling, the American Academy of Pediatrics, Aspen Institute Project Play, and the National Wrestling Coaches Association."


def parent_ten_html():
    items = "".join(f'<li><span class="pt-n">{i}</span><div><b>{a}</b><span>{b}</span></div></li>' for i, (a, b) in enumerate(PARENT_TEN, 1))
    return f"""<section class="band pt" aria-labelledby="pt-title">
  <div class="wrap ym-wrap">
    <p class="ym-label">For youth parents</p>
    <h2 id="pt-title">How to be a Konkrete Kids parent</h2>
    <p class="ym-lede-dark">Ten things that matter most.</p>
    <ol class="pt-list" role="list">{items}</ol>
    <p class="pt-closer">{PARENT_CLOSER}</p>
    <p class="ym-src">{PARENT_SOURCES}</p>
    <p class="actions"><a class="btn ghost dark-ink" href="parent-guide/" target="_blank" rel="noopener">Printable one-pager</a></p>
  </div>
</section>
"""


def build_parent_guide():
    """Standalone printable one-pager (fits one letter page). youth/parent-guide/"""
    items = "".join(f'<li><span class="n">{i}</span><div><b>{a}</b> {b}</div></li>' for i, (a, b) in enumerate(PARENT_TEN, 1))
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>How to Be a Konkrete Kids Parent | {SITE['name']}</title>
<meta name="description" content="Ten things that matter most for Northampton youth wrestling parents.">
<link rel="canonical" href="{SITE['domain']}/youth/parent-guide/">
<link rel="icon" href="../../assets/img/logo-96.png">
<style>
@font-face {{ font-family: "Anton"; src: url("../../assets/fonts/anton-400.woff2") format("woff2"); }}
@font-face {{ font-family: "Inter"; src: url("../../assets/fonts/inter-var.woff2") format("woff2"); font-weight: 100 900; }}
@page {{ size: letter; margin: 0.45in; }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html, body {{ margin: 0; background: #e6e4df; color: #141414; font-family: "Inter", system-ui, sans-serif; }}
.sheet {{ background: #fff; max-width: 8.5in; margin: 24px auto; padding: 0.5in 0.55in; box-shadow: 0 2px 18px rgba(0,0,0,.15); }}
header {{ display: flex; align-items: center; gap: 18px; border-bottom: 6px solid #f26a1b; padding-bottom: 14px; margin-bottom: 18px; }}
header img {{ width: 78px; height: auto; }}
.kick {{ font-family: "Anton", Impact, sans-serif; letter-spacing: .16em; text-transform: uppercase; color: #9c3d08; font-size: 13px; margin: 0 0 4px; }}
h1 {{ font-family: "Anton", Impact, sans-serif; font-weight: 400; text-transform: uppercase; font-size: 40px; line-height: 1; margin: 0; }}
h1 span {{ color: #f26a1b; }}
.sub {{ margin: 6px 0 0; color: #5c5a55; font-size: 15px; }}
ol {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 11px; }}
li {{ display: flex; gap: 14px; align-items: flex-start; font-size: 15.5px; line-height: 1.4; padding-bottom: 11px; border-bottom: 1px solid #e3e0da; }}
li:last-child {{ border-bottom: 0; padding-bottom: 0; }}
.n {{ flex: 0 0 34px; height: 34px; border-radius: 50%; background: #141414; color: #f26a1b; display: grid; place-items: center; font-family: "Anton", Impact, sans-serif; font-size: 18px; }}
li:nth-child(even) .n {{ background: #f26a1b; color: #141414; }}
li b {{ font-weight: 800; }}
.closer {{ margin: 20px 0 10px; background: #141414; color: #fff; border-radius: 8px; padding: 14px 18px; text-align: center; font-family: "Anton", Impact, sans-serif; text-transform: uppercase; font-size: 20px; letter-spacing: .02em; }}
.closer span {{ color: #f26a1b; }}
.src {{ font-size: 11.5px; color: #5c5a55; margin: 0; text-align: center; }}
.bar {{ max-width: 8.5in; margin: 16px auto 0; display: flex; gap: 10px; justify-content: flex-end; padding: 0 4px; }}
.bar a, .bar button {{ font: 700 15px "Inter", sans-serif; padding: 10px 16px; border-radius: 4px; border: 2px solid #141414; background: #fff; color: #141414; cursor: pointer; text-decoration: none; }}
.bar button {{ background: #f26a1b; border-color: #f26a1b; }}
@media (max-width: 640px) {{ .sheet {{ margin: 12px; padding: 22px 18px; }} h1 {{ font-size: 30px; }} header img {{ width: 56px; }} .bar {{ margin: 12px; }} }}
@media print {{ html, body {{ background: #fff; }} .bar {{ display: none; }} .sheet {{ box-shadow: none; margin: 0; padding: 0; max-width: none; }} h1 {{ font-size: 44px; }} li {{ font-size: 17px; padding-bottom: 12px; }} ol {{ gap: 12px; }} .n {{ flex-basis: 40px; height: 40px; font-size: 21px; }} .closer {{ font-size: 22px; margin-top: 20px; }} .src {{ font-size: 12.5px; }} }}
</style></head>
<body>
<div class="bar"><a href="../">Back to Youth Wrestling</a><button type="button" onclick="window.print()">Print</button></div>
<main class="sheet">
  <header><img src="../../assets/img/logo-192.png" alt="Northampton Konkrete Kids logo" width="78" height="78">
    <div><p class="kick">Northampton Youth Wrestling · Konkrete Kids</p><h1>How to be a <span>Konkrete Kids</span> parent</h1><p class="sub">Ten things that matter most.</p></div></header>
  <ol>{items}</ol>
  <p class="closer">{PARENT_CLOSER.replace("It’s their thing", "<span>It’s their thing").replace("not ours.", "not ours.</span>")}</p>
  <p class="src">{PARENT_SOURCES}</p>
</main>
</body></html>
"""
    dest = os.path.join(ROOT, "youth/parent-guide/index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(html)
    return SITE["domain"] + "/youth/parent-guide/"


def build_youth():
    yc_promo = """<section class="band dark yc-promo">
  <div class="wrap split narrow-right">
    <div><p class="kicker">For youth coaches</p><h2>Youth Coaches’ Playbook</h2>
    <p class="lede">What to teach in Novice and in Orange &amp; Black, what each wrestler should be able to demonstrate, and how to run a practice.</p></div>
    <p class="actions"><a class="btn" href="coaches/">Open the playbook</a></p>
  </div>
</section>
""" if YOUTH_COACHES_LIVE else ""
    R = "../"
    body = f"""
{page_head(R, "Youth Wrestling", "Grades K–6. Where every Konkrete Kid starts.", "youth-champs", "50% 18%")}
<nav class="yj" aria-label="On this page"><div class="wrap"><a class="yj-main" href="#join">Register</a><a href="#ym-title">Two Teams</a><a href="#pt-title">Parent Guide</a><a href="#faq">FAQs</a></div></nav>
<section class="band">
  <div class="wrap split narrow-right">
    <div class="prose">
      <h2>Northampton youth wrestling</h2>
      <p>Our youth program competes in the Valley Elementary Wrestling League (VEWL) for wrestlers in kindergarten through 6th grade. More than 100 kids wrestle each year on three teams:</p>
      <ul class="results" role="list"><li><span>Northampton Black</span><b>Varsity and JV</b></li><li><span>Northampton Orange</span><b>Varsity and JV</b></li><li><span>Novice</span><b>Grades K–2</b></li></ul>
      <p>The goal is simple: carry on the tradition of Northampton wrestling, teach strong fundamentals, and build friendships and a community that last long after the season ends. Many of today’s varsity wrestlers and coaches started right here.</p>
    </div>
    <aside class="note-card" id="join">
      <h3>Join the Konkrete Kids</h3>
      <p>Registration runs through the NAA youth program. Sign up online.</p>
      <p class="actions"><a class="btn" href="{SITE['links']['youth_registration']}" rel="noopener" target="_blank">Register for youth wrestling</a></p>
    </aside>
  </div>
</section>
{youth_model_html()}{parent_ten_html()}
{yc_promo}<section class="band concrete">
  <div class="wrap">
    <h2 id="faq">Questions families ask</h2>
    <div class="faq">
      <details><summary>Who can wrestle?</summary><p>Boys and girls in kindergarten through 6th grade.</p></details>
      <details><summary>Does my child need experience?</summary><p>No. Novice is generally for grades K–2 and focuses on fun and fundamentals. An experienced 2nd grader may move up to Black or Orange.</p></details>
      <details><summary>How are wrestlers placed on Black and Orange?</summary><p>As a team. Black, Orange, and Novice coaches place wrestlers together, so each team gets an even mix of experience levels and weights. No team is ranked above the other.</p></details>
      <details><summary>Won’t this hold back our more advanced wrestlers?</summary><p>No. Black and Orange varsity and JV still practice together, so advanced wrestlers keep training with experienced partners.</p></details>
      <details><summary>Will my child still get strong competition?</summary><p>Yes. Each team has its own full schedule, and Black and Orange wrestle each other during the season.</p></details>
      <details><summary>Will current wrestlers change teams?</summary><p>Some may, to help balance the rosters. Most of the shift happens gradually, as each new class moves up from Novice.</p></details>
      <details><summary>Isn’t earning your spot a good lesson?</summary><p>Yes, and wrestlers still earn varsity spots. A JV wrestler can move up to varsity during the season, so there’s always a goal to chase.</p></details>
      <details><summary>What if my child outgrows their team?</summary><p>We’ll move them. If a wrestler is stuck behind a teammate at the same weight, coaches can move them so both wrestlers get a varsity spot.</p></details>
      <details><summary>Why is this happening gradually?</summary><p>Big changes work best in steps. Each new class moving up from Novice is placed to keep the teams even, and both rosters balance out over a few seasons. Schedules are set by the previous year’s results, so they’ll even out as the teams do.</p></details>
      <details><summary>How does this help the whole program?</summary><p>More kids who stay in wrestling means deeper junior high and high school rosters. Wrestlers also reach the junior high as experienced teammates who already know how to compete together.</p></details>
      <details><summary>What happens after 6th grade?</summary><p>Wrestlers move up to the <a href="../junior-high/">junior high team</a> in 7th grade (the junior high team is grades 7–9; 9th graders can wrestle junior high or high school), then to the <a href="../high-school/">high school</a> program.</p></details>
      <details><summary>Can we still share feedback?</summary><p>Absolutely. The direction is set, and the details are reviewed every season. We’re always willing to listen: email <a href="mailto:{SITE['email']}">{SITE['email']}</a>.</p></details>
    </div>
  </div>
</section>
<section class="band">
  <div class="wrap">
    <div class="duo">
      {figure(R, "youth-autographs", "(min-width: 900px) 45vw, 100vw")}
      {figure(R, "youth-mat", "(min-width: 900px) 45vw, 100vw")}
    </div>
    <h2 class="sub top-gap">More from the youth program</h2>
    {gallery(R, ["youth-varsity-mat", "youth-team-2022", "youth-novice-2022", "youth-autographs-2"], "youth")}
  </div>
</section>
"""
    return page("youth/index.html", "Youth", "Northampton youth wrestling for grades K–6 in the Valley Elementary Wrestling League.", body, "youth/", og_image="youth-champs")


YC_POSITIONS = [("feet", "On Our Feet"), ("bottom", "Bottom"), ("top", "Top")]
YC_TYPES = {"drill": "Northampton drill", "live": "Live situation", "game": "Game"}

# Which library drills a skill uses: its drill style (2&2 or partner) plus any
# drill or live situation its text names.
YC_DRILL_KEYS = [("Stance in", "stance-in-out"), ("Shadow wrestle", "shadow"), ("Mirror", "mirror"),
                 ("Whistle drill", "whistle"), ("Coach calls a position", "ladder"), ("Hand-fight drill", "hand-fight"),
                 ("Live hand fight", "hand-fight"), ("Foot touch", "foot-touch"), ("two commands", "changeover"),
                 ("Live once in", "live-leg"), ("On knees: one shoots", "knees-shoot"), ("On knees: snap", "knees-shoot"),
                 ("On belly", "belly"), ("Half nelson", "half"), ("Tie-ups", "tie-ups"), ("Start in a tie", "tie-ups"),
                 ("leg in", "legs"), ("legs in", "legs"), ("Quick starts", "quick-starts"), ("Overtime", "ride-out"),
                 ("Ankle touch", "ankle-touch"), ("Series", "series")]


def yc_id(s):
    return f'{s["level"]}-{slug(s["name"])}'


def yc_drill_head(lid):
    return "Drill (review principles)" if lid == "novice" else "2&2 Drill (review principles)"


def yc_skill_drills(s):
    ids = ["partner-drill" if s["level"] == "novice" else "two-and-two"]
    text = s.get("drill", "") + " " + s.get("live", "")
    for k, did in YC_DRILL_KEYS:
        if k.lower() in text.lower() and did not in ids:
            ids.append(did)
    return ids


def yc_sheet(smp, by_id):
    """One practice plan in the layout of Joe's high school template."""
    def moves(ids, new=False):
        out = ""
        for i in ids:
            x = by_id[i]
            cues = "".join(f"<li>{e(c)}</li>" for c in x.get("teach", []))
            out += f'<li>{e(x["name"])}{" <em>(new)</em>" if new else ""}{f"<ul>{cues}</ul>" if cues else ""}</li>'
        return out
    plain = lambda items: "".join(f"<li>{e(t)}</li>" for t in items)
    notes = plain([f'{by_id[i]["name"]}: {by_id[i]["demonstrates"]}' for i in smp["new"]] + ["Who needs it re-taught next practice?"])
    secs = [("Announcements", plain(smp["announcements"])), ("Warm-up", plain(smp["warmup"])),
            (yc_drill_head(smp["level"]), moves(smp["review"])), ("New Technique", moves(smp["new"], True)),
            ("Contest situation", plain(smp["contest"])), ("Conditioning", plain(smp["conditioning"])),
            ("Announcements", plain(smp["closing"]) or "<li></li>"), ("Team Culture", plain(smp["culture"])), ("My notes", notes)]
    body = "".join(f'<section><h4>{e(n)}</h4><ul>{c}</ul></section>' for n, c in secs)
    return (f'<div class="yc-sheet">{yc_sheet_head(e(smp["title"].split(": ", 1)[-1]))}'
            f'<div class="yc-sheet-body">{body}</div>{YC_SHEET_FOOT}</div>')


YC_SHEET_FOOT = '<div class="yc-sheet-foot"><span>Better people first. Better wrestlers along the way.</span><span>Konkrete Kids</span></div>'


def yc_sheet_head(meta):
    return ('<div class="yc-sheet-head"><img class="yc-logo" src="../../assets/img/logo-192.png" width="192" height="165" alt="Northampton Wrestling">'
            f'<div class="yc-sheet-title"><p>Northampton Wrestling · Youth</p><h3>Practice Plan</h3></div><span class="yc-sheet-meta">{meta}</span></div>')


def yc_skill(s, drills):
    cues = "".join(f"<li>{e(c)}</li>" for c in s.get("teach", []))
    teach = (f'<p class="ycp-label">Teach</p><ul class="ycp-cues">{cues}</ul>' if cues else
             '<p class="ycp-label">Teach</p><p class="ycp-small">Demonstrate it, then walk it through at half speed.</p>')
    how = e(s["drill"]) + (f' <span class="ycp-arrow">→</span> {e(s["live"])}' if s.get("live") else "")
    chips = "".join(f'<a class="ycp-chip" href="#drill-{d}">{e(drills[d]["name"])} ↗</a>' for d in yc_skill_drills(s) if d in drills)
    vid = (f'<p class="ycp-label">Watch technique</p><p class="ycp-chips"><a class="ycp-chip dark" href="{e(s["video"])}" rel="noopener" target="_blank">▶ {e(s["name"])} ↗</a></p>'
           if s.get("video") else "")
    return (f'<article class="ycp-skill" id="{yc_id(s)}"><h4>{e(s["name"])}</h4>{teach}'
            f'<p class="ycp-label">Coach it this way</p><p class="ycp-small">{how}</p>'
            f'<p class="ycp-demo"><b>Wrestler demonstrates:</b> {e(s["demonstrates"])}</p>'
            f'<p class="ycp-label">Run these drills</p><p class="ycp-chips">{chips}</p>{vid}'
            f'<a class="ycp-mini" href="#builder" data-level="{s["level"]}" data-skill="{yc_id(s)}">Build a practice with this skill →</a></article>')


def yc_level(YC, lid, drills):
    lv = YC["levels"][lid]
    skills = [s for s in YC["skill"] if s["level"] == lid]
    blocks = []
    for pi, (pid, pname) in enumerate(YC_POSITIONS):
        ps = [s for s in skills if s["position"] == pid]
        note = lv.get("notes", {}).get(pid)
        groups = list(dict.fromkeys(s.get("group", "") for s in ps))
        inner = f'<p class="ycp-callout">{e(note)}</p>' if note else ""
        for g in groups:
            head = f'<h4 class="ycp-group">{e(g)}</h4>' if g else ""
            inner += head + '<div class="ycp-grid2">' + "".join(yc_skill(s, drills) for s in ps if s.get("group", "") == g) + "</div>"
        blocks.append(f'<details class="ycp-acc" id="{lid}-{pid}"{" open" if pi == 0 else ""}><summary><span>{pname}</span>'
                      f'<span class="ycp-count">{len(ps)} skills</span></summary><div class="ycp-acc-body">{inner}</div></details>')
    attitude = "".join(f"<li>{e(a)}</li>" for a in lv["attitude"])
    habits = "".join(f"<li>{e(h)}</li>" for h in lv["habits"])
    live = ""
    for L in [x for x in YC["live"] if x["level"] == lid]:
        h = f'<p class="ycp-label">{e(L["group"])}</p>' if L.get("group") else ""
        live += f'<div>{h}<ul class="ycp-list">{"".join(f"<li>{e(i)}</li>" for i in L["items"])}</ul></div>'
    live_lead = "" if lid == "novice" else '<p class="ycp-small">Everything in Novice, plus:</p>'
    ct, cb = lv["callout"]
    return f"""
    <div class="ycp-banner"><div><p class="ycp-eyebrow light">{e(lv["who"])}</p><h3>{e(lv["name"])}</h3><p>{e(lv["summary"])}</p></div><span class="ycp-big">{e(lv["label"])}</span></div>
    <p class="ycp-note"><b>{e(ct)}</b> {e(cb)}</p>
    <div class="ycp-card ycp-attitude"><p class="ycp-eyebrow">Attitude · the Northampton way</p><ul>{attitude}</ul></div>
    <div class="ycp-row"><h3>Three positions</h3><p>Tap a position to open teaching steps, drill links and videos.</p></div>
    {"".join(blocks)}
    <div class="ycp-grid2 ycp-gap">
      <div class="ycp-card"><h3>Non-negotiable coaching habits</h3><ul class="ycp-checks">{habits}</ul></div>
      <div class="ycp-card"><h3>Teaching distinction</h3><p>{e(lv["distinction"])}</p>
        <p><span class="ycp-pill">Practice length: coming soon</span></p>
        <a class="ycp-btn soft" href="#builder" data-level="{lid}">Build a practice for this level →</a></div>
    </div>
    <div class="ycp-card ycp-gap"><h3>Live situations</h3>{live_lead}<div class="ycp-grid2 tight">{live}</div></div>"""


def yc_drill_card(d, used):
    rows = "".join(f'<div><dt>{k}</dt><dd>{e(d[f])}</dd></div>' for k, f in
                   [("Set-up", "setup"), ("Coach this", "coach"), ("Coaching cue", "cue"), ("Check learning", "check")])
    groups = " · ".join({"novice": "Novice", "orange-black": "Orange & Black"}[x] for x in d["levels"])
    pos = "All positions" if d["position"] == "all" else dict(YC_POSITIONS)[d["position"]]
    used_txt = f'<p class="ycp-small muted">Used for: {e(", ".join(used[:5]))}{"…" if len(used) > 5 else ""}</p>' if used else ""
    return (f'<article class="ycp-card ycp-drill" id="drill-{d["id"]}" data-levels="{" ".join(d["levels"])}" data-position="{d["position"]}" data-type="{d["type"]}">'
            f'<p class="ycp-chips"><span class="ycp-chip type-{d["type"]}">{YC_TYPES[d["type"]]}</span><span class="ycp-chip dark">{pos}</span></p>'
            f'<h3>{e(d["name"])}</h3><p class="ycp-small muted">{groups}</p><dl class="ycp-dl">{rows}</dl>'
            f'<p class="ycp-chips foot"><button type="button" class="ycp-chip" data-copy-drill>Copy drill</button></p>{used_txt}</article>')


def build_youth_coaches():
    R = "../../"
    YC = load_toml("youth-coaches.toml")
    I, H, P, D = YC["intro"], YC["hero"], YC["practice"], YC["drilling"]
    lids = list(YC["levels"].keys())
    drills = {d["id"]: d for d in YC["drill"]}
    used = {}
    for s in YC["skill"]:
        for did in yc_skill_drills(s):
            used.setdefault(did, []).append(s["name"])
    by_id = {yc_id(x): x for x in YC["skill"]}
    lvl_name = lambda lid: YC["levels"][lid]["name"]
    level_opts = "".join(f'<option value="{lid}">{e(lvl_name(lid))}</option>' for lid in lids)
    top = '<p class="ycp-top"><a href="#top">↑ Back to the top</a></p>'
    # Hero mat graphic: a wrestling mat with the center circle, starting lines and two wrestlers
    mat = f"""<figure class="ycp-mat" aria-hidden="true"><svg viewBox="0 0 460 300" focusable="false">
      <defs><radialGradient id="matg" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#2a2522"/><stop offset="1" stop-color="#151619"/></radialGradient></defs>
      <rect width="460" height="300" fill="url(#matg)"/>
      <circle cx="230" cy="150" r="170" fill="none" stroke="#f26a1b" stroke-width="14" opacity=".9"/>
      <circle cx="230" cy="150" r="128" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="2"/>
      <circle cx="230" cy="150" r="30" fill="none" stroke="rgba(255,255,255,.75)" stroke-width="2"/>
      <rect x="196" y="146" width="22" height="8" rx="2" fill="#f26a1b"/><rect x="242" y="146" width="22" height="8" rx="2" fill="#fff"/>
      <path d="M150 210 C 175 150, 205 125, 230 150" fill="none" stroke="#f9a46e" stroke-width="2.5" stroke-dasharray="6 6"/>
      <circle cx="150" cy="214" r="19" fill="#f26a1b" stroke="#151619" stroke-width="4"/><text x="150" y="221" text-anchor="middle" font-family="Inter, sans-serif" font-weight="800" font-size="20" fill="#151619">1</text>
      <circle cx="318" cy="112" r="19" fill="#fff" stroke="#151619" stroke-width="4"/><text x="318" y="119" text-anchor="middle" font-family="Inter, sans-serif" font-weight="800" font-size="20" fill="#151619">2</text>
    </svg><figcaption>{e(H["mat_caption"])}</figcaption></figure>"""
    hero = f"""<header class="ycp-hero" id="top"><div class="wrap ycp-hero-grid">
  <div><p class="ycp-eyebrow">{e(H["eyebrow"])}</p>
    <h1>{"<br>".join(e(x) for x in H["lines"])}<br><span>{e(H["accent"])}</span></h1>
    <p class="ycp-lede">{e(H["lede"])}</p>
    <p class="ycp-actions"><a class="ycp-btn" href="#builder">Build a practice →</a><a class="ycp-btn dark" href="#expectations">Your level’s standards →</a><a class="ycp-btn dark" href="#videos">▶ Technique videos</a></p></div>
  {mat}</div></header>"""
    tabs = [("standard", "The standard"), ("expectations", "Level expectations"), ("builder", "Practice builder"),
            ("drills", "Drill library"), ("videos", "Video library"), ("challenge", "Coaching challenge"), ("checkin", "Weekly check-in")]
    tabbar = '<nav class="ycp-tabs" aria-label="Playbook sections"><div class="wrap">' + "".join(f'<a href="#{i}">{t}</a>' for i, t in tabs) + "</div></nav>"
    std = "".join(f'<li class="ycp-card"><p class="ycp-eyebrow">{i + 1:02d} · {e(k)}</p><h3>{e(t)}</h3><p>{e(d)}</p></li>' for i, (k, t, d) in enumerate(I["standard"]))
    road = "".join(f'<li class="ycp-card"><span class="ycp-num">{i + 1}</span><div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>' for i, (t, d) in enumerate(I["roadmap"]))
    HB, SU, DV = YC["habit"], YC["success"], YC["development"]
    panels = "".join(f'<div class="ycp-panel" id="lvl-{lid}" data-level-panel="{lid}">{yc_level(YC, lid, drills)}</div>' for lid in lids)
    template = "".join(f"<li><b>{e(a)}</b> {e(b)}</li>" for a, b in P["sections"])
    samples = "".join(f'<details class="ycp-acc small"><summary><span>{e(smp["title"])}</span></summary><div class="ycp-acc-body">{yc_sheet(smp, by_id)}</div></details>' for smp in YC["sample"])
    drill_cards = "".join(yc_drill_card(d, used.get(d["id"], [])) for d in YC["drill"])
    videos = [s for s in YC["skill"] if s.get("video")]
    if videos:
        vids = '<div class="ycp-grid3">' + "".join(
            f'<article class="ycp-card"><p class="ycp-chips"><span class="ycp-chip dark">{dict(YC_POSITIONS)[s["position"]]}</span></p><h3>{e(s["name"])}</h3>'
            f'<p class="ycp-small muted">{e(lvl_name(s["level"]))}</p><a class="ycp-btn dark sm" href="{e(s["video"])}" rel="noopener" target="_blank">▶ Watch demonstration ↗</a></article>'
            for s in videos) + "</div>"
    else:
        vids = ('<div class="ycp-note bar"><b>Northampton technique videos are coming.</b> When a video is added to a skill, it shows up here '
                'and as a “Watch technique” button on that skill’s card.</div>')
    scen = YC["scenario"]
    noscript_quiz = "".join(f'<details class="ycp-acc small"><summary><span>{e(q["q"])}</span></summary><div class="ycp-acc-body"><p><b>{e(q["options"][q["answer"]])}</b></p><p>{e(q["why"])}</p></div></details>' for q in scen)
    C = YC["checkin"]
    standards = "".join(f"<li>{e(x)}</li>" for x in YC["standards"]["items"])
    bdata = {
        "levels": {lid: {"name": lv["name"], "warmup": lv["warmup"], "conditioning": lv["conditioning"], "drill": yc_drill_head(lid)} for lid, lv in YC["levels"].items()},
        "positions": dict(YC_POSITIONS),
        "skills": [{"id": yc_id(x), "level": x["level"], "position": x["position"], "name": x["name"], "teach": x.get("teach", []),
                    "drill": x["drill"], "live": x.get("live", ""), "demo": x["demonstrates"], "drills": yc_skill_drills(x)} for x in YC["skill"]],
        "drills": {d["id"]: {"name": d["name"], "setup": d["setup"], "coach": d["coach"], "cue": d["cue"], "check": d["check"],
                             "type": d["type"], "levels": d["levels"]} for d in YC["drill"]},
        "live": {lid: [i for L in YC["live"] if L["level"] in (lid, "novice") and (lid != "novice" or L["level"] == "novice") for i in L["items"]] for lid in lids},
        "quiz": scen,
        "checkin": {"common": C["common"], "levels": {k: v["items"] for k, v in C["levels"].items()}},
    }
    bjson = json.dumps(bdata, ensure_ascii=False).replace("</", "<\\/")
    body = f"""
<div class="ycp">
{hero}
{tabbar}
<section class="ycp-sec" id="standard" aria-labelledby="standard-title"><div class="wrap">
  <p class="ycp-eyebrow">Our shared commitment</p><h2 id="standard-title">A consistent foundation. Across every team.</h2>
  <p class="ycp-intro">Coaches bring their own personalities and styles. But the skills we teach, and the habits we reinforce, should not depend on which team a child joins.</p>
  <ol class="ycp-grid4">{std}</ol>
  <div class="ycp-split ycp-gap top">
    <div class="ycp-card dark"><p class="ycp-eyebrow light">{e(HB["eyebrow"])}</p><h3>{e(HB["title"])}</h3><p>{e(HB["text"])}</p><p class="ycp-chain">{e(HB["chain"])}</p></div>
    <div class="ycp-card"><p class="ycp-eyebrow">{e(SU["eyebrow"])}</p><h3>{e(SU["title"])}</h3><p>{e(SU["text"])}</p>
      <dl class="ycp-success">{"".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in SU["items"])}</dl>
      <p class="ycp-small muted">{e(SU["outro"])}</p><a class="ycp-btn soft" href="../../junior-high/">{e(SU["link_text"])} →</a></div>
  </div>
  <div class="ycp-note bar ycp-gap"><b>{e(DV["title"])}</b> {e(DV["text"])}</div>
  <p class="ycp-eyebrow ycp-gap-lg">The development process</p><h2>Four steps to an effective season</h2>
  <ol class="ycp-grid4 ycp-steps">{road}</ol>
  <div class="ycp-split ycp-gap">
    <div class="ycp-card"><p class="ycp-eyebrow">Our mission</p><p>{e(I["mission"])}</p><p class="ycp-tagline">{e(I["tagline"])}</p></div>
    <div class="ycp-card"><p class="ycp-eyebrow">One program, K–12</p><p>{e(I["northampton_way"])}</p></div>
  </div>
  {top}
</div></section>

<section class="ycp-sec alt" id="expectations" aria-labelledby="exp-title"><div class="wrap">
  <p class="ycp-eyebrow">Developmental progression</p><h2 id="exp-title">What should wrestlers learn—and how?</h2>
  <p class="ycp-intro">Select your level, Novice or Orange &amp; Black, for its attitude, the skills in each position, how to coach each one, the drills to run, and what a wrestler must demonstrate before moving on.</p>
  <label class="ycp-field">Select your level<select id="ycp-level">{level_opts}</select></label>
  {panels}
  {top}
</div></section>

<section class="ycp-sec" id="builder" aria-labelledby="builder-title"><div class="wrap">
  <p class="ycp-eyebrow">Plan your next practice</p><h2 id="builder-title">Build a purposeful practice.</h2>
  <p class="ycp-intro">{e(P["intro"])} Choose the level, the moves to review and the new technique. The plan fills in the cues, the contest situation and what to check.</p>
  <div class="yc-builder" data-builder hidden>
    <div class="ycp-card ycp-form">
      <div class="ycp-form-row">
        <label class="ycp-field">Level<select id="b-level">{level_opts}</select></label>
        <label class="ycp-field">Date<input type="date" id="b-date"></label>
        <label class="ycp-field">New technique<select id="b-skill1"></select></label>
        <label class="ycp-field">Second new technique <span class="muted">(optional)</span><select id="b-skill2"></select></label>
      </div>
      <details class="ycp-review"><summary>Review moves <span class="muted" id="b-review-count"></span></summary><div class="yc-checklist" id="b-review"></div></details>
    </div>
    <div class="ycp-split wide ycp-gap">
      <div class="yc-out"><div class="ycp-edit-hint"><p><b>Make it yours.</b> Click any line to change it. Use + Add line or × to add and remove lines. Your plan saves on this device.</p>
        <button type="button" class="ycp-btn soft sm" id="b-fresh">Start a fresh plan</button></div><div id="b-sheet"></div></div>
      <div class="ycp-side">
        <div class="ycp-card"><p class="ycp-eyebrow">Run these drills</p><div id="b-drills"></div></div>
        <div class="ycp-card"><p class="ycp-eyebrow">Exit check: not just activity</p><h3>Can they actually do it?</h3>
          <p>At the end, ask 3–5 wrestlers to demonstrate today’s skill. If most can’t do it under light pressure, keep it as the priority next practice.</p></div>
        <p class="ycp-actions"><button type="button" class="ycp-btn" id="b-copy">Copy plan</button><button type="button" class="ycp-btn soft" id="b-print">Print plan</button></p>
      </div>
    </div>
  </div>
  <noscript><p class="ycp-note">Turn on JavaScript to use the practice builder, or use the template below.</p></noscript>
  <div class="ycp-split ycp-gap">
    <div class="ycp-card"><h3>The practice plan, section by section</h3><ol class="ycp-template">{template}</ol></div>
    <div><div class="ycp-card"><h3>2&amp;2 drilling <span class="ycp-pill">Orange &amp; Black</span></h3><p>{e(D["two_and_two"])}</p><p>{e(D["series"])}</p><p class="ycp-small muted">Novice does not drill 2&amp;2.</p></div>
      <div class="ycp-gap">{samples}</div></div>
  </div>
  {top}
</div></section>

<section class="ycp-sec alt" id="drills" aria-labelledby="drills-title"><div class="wrap">
  <p class="ycp-eyebrow">Coach-ready drill instructions</p><h2 id="drills-title">The drill library coaches can actually use.</h2>
  <p class="ycp-intro">Every drill, live situation and game in the playbook, with the set-up, what to coach, the cue, and how to check learning.</p>
  <div class="ycp-filters" data-drill-filters hidden>
    <label class="ycp-field">Level<select id="f-level"><option value="">All levels</option>{level_opts}</select></label>
    <label class="ycp-field">Position<select id="f-pos"><option value="">All positions</option>{"".join(f'<option value="{k}">{v}</option>' for k, v in YC_POSITIONS)}</select></label>
    <label class="ycp-field">Type<select id="f-type"><option value="">All types</option><option value="drill">Drills</option><option value="live">Live situations</option><option value="game">Games</option></select></label>
  </div>
  <p class="ycp-small muted" id="f-count">{len(YC["drill"])} drills, live situations and games.</p>
  <div class="ycp-grid3">{drill_cards}</div>
  {top}
</div></section>

<section class="ycp-sec" id="videos" aria-labelledby="videos-title"><div class="wrap">
  <p class="ycp-eyebrow">Coach demonstration videos</p><h2 id="videos-title">See the technique. Run the drill.</h2>
  <p class="ycp-intro">Watch the technique, then use the cues and drills in your next practice.</p>
  {vids}
  {top}
</div></section>

<section class="ycp-sec alt" id="challenge" aria-labelledby="challenge-title"><div class="wrap">
  <p class="ycp-eyebrow">5-minute coaching check</p><h2 id="challenge-title">Can you make the right coaching decision?</h2>
  <p class="ycp-intro">Work through real situations and choose the response that lives our standards.</p>
  <div class="ycp-card ycp-quiz" data-quiz hidden>
    <div class="ycp-progress"><span id="q-bar"></span></div>
    <p class="ycp-eyebrow" id="q-num"></p><h3 id="q-text"></h3>
    <div class="ycp-options" id="q-opts"></div>
    <div class="ycp-feedback" id="q-fb" hidden></div>
    <div class="ycp-quiz-foot"><p class="ycp-small muted">Find a coaching solution, not just an answer.</p><button type="button" class="ycp-btn" id="q-next" disabled>Next scenario →</button></div>
  </div>
  <noscript>{noscript_quiz}</noscript>
  {top}
</div></section>

<section class="ycp-sec" id="checkin" aria-labelledby="checkin-title"><div class="wrap">
  <p class="ycp-eyebrow">A repeatable standard</p><h2 id="checkin-title">60-second weekly coaching check-in</h2>
  <p class="ycp-intro">{e(C["intro"])}</p>
  <label class="ycp-field">Select your level<select id="c-level">{level_opts}</select></label>
  <div class="ycp-split wide ycp-gap">
    <div class="ycp-card" data-checkin hidden><h3 id="c-title">After-practice reflection</h3>
      <p class="ycp-small muted">Check what genuinely happened this week. Unchecked boxes are next practice’s teaching priority, not a failure.</p>
      <div class="ycp-progress"><span id="c-bar"></span></div><p class="ycp-small" id="c-count"></p>
      <div class="ycp-checkgrid" id="c-items"></div>
      <p class="ycp-actions"><button type="button" class="ycp-btn" id="c-copy">Copy check-in summary</button><button type="button" class="ycp-btn soft" id="c-reset">Start a new week</button></p></div>
    <div class="ycp-card"><p class="ycp-eyebrow">Observe, don’t assume</p><h3>The question worth asking</h3><p><b>{e(C["question"])}</b></p><p>{e(C["answer"])}</p><p class="ycp-good">{e(C["start"])}</p></div>
  </div>
  {top}
</div></section>

<section class="ycp-sec dark" id="standards" aria-labelledby="standards-title"><div class="wrap">
  <p class="ycp-eyebrow light">How we coach Konkrete Kids</p><h2 id="standards-title">Coaching standards</h2>
  <p class="ycp-intro">We are transformational coaches. Kids learn what a good adult looks like by watching us.</p>
  <ol class="ycp-standards">{standards}</ol>
  <p class="ycp-actions ycp-gap"><a class="ycp-btn" href="../">Youth wrestling home</a></p>
</div></section>
</div>
<script type="application/json" id="yc-data">{bjson}</script>
"""
    return page("youth/coaches/index.html", "Youth Coaches’ Playbook",
                "What Northampton youth wrestling coaches teach: Novice and Orange & Black skills, how to coach each one, a practice builder, a drill library, and coaching standards.",
                body, "youth/coaches/", scripts=("site.js", "coaches.js"), og_image="youth-mat")


def build_coaches():
    R = "../"
    h = COACHES["head"]

    def coach_card(c):
        if c["photo"]:
            ph = picture(R, c["photo"], "180px", "avatar")
        else:
            ini = "".join(x[0] for x in c["name"].split())
            ph = f'<span class="avatar initials" aria-hidden="true">{ini}</span>'
        return f'<article class="coach">{ph}<div><h3>{e(c["name"])}</h3><p class="role">{e(c["role"])}</p><p>{e(c["bio"])}</p></div></article>'

    body = f"""
{page_head(R, "Coaching Staff", "The coaches who run the room, from the varsity to the junior high.", "staff-states-2026", "50% 22%", cls="fit-photo")}
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
      <p><b>{h['record']}</b> Dual Record</p>
      <p><b>{h['district_champs']}</b> District XI Champions</p>
      <p><b>{h['regional_champs']}</b> Northeast Regional Champions</p>
      <p><b>{h['state_champs']}</b> State Champions</p>
      <p><b>{h['placewinners']}</b> State Placewinners</p>
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
      {figure(R, "coaches-embrace", "(min-width: 900px) 30vw, 100vw")}
      {figure(R, "bench-final-seconds", "(min-width: 900px) 30vw, 100vw")}
      {figure(R, "staff-corner", "(min-width: 900px) 30vw, 100vw")}
    </div>
  </div>
</section>
"""
    return page("coaching-staff/index.html", "Coaching Staff", "Northampton wrestling coaching staff: head coach Joe Provini, varsity assistants, and junior high coaches.", body, "coaching-staff/", og_image="staff-states-2026")


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
        return (f'<div class="table-wrap" tabindex="0"><table class="hall" id="{id_}"><caption>{cap}</caption><thead><tr>{th}</tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')

    tr = lambda r, extra="": (f'<tr data-name="{e(" ".join([norm(r["wrestler"])] + SEARCH_ALIASES.get(norm(r["wrestler"]), [])))}"><td>{r["year"]}</td><th scope="row">{e(r["wrestler"])}</th>'
                              f'<td>{r["weight"]}</td>{extra}</tr>')
    t_medals = tbl("t-medals", "PIAA State Medalists, newest first", ["Year", "Wrestler", "Weight", "Place"],
                   "".join(tr(r, f'<td class="{"gold" if r["place"] == "1" else ""}">{PLACE[r["place"]]}</td>') for r in medals))
    t_reg = tbl("t-reg", "Northeast Regional Champions, newest first", ["Year", "Wrestler", "Weight"], "".join(tr(r) for r in HALL["regional"][::-1]))
    t_dist = tbl("t-dist", "District XI Champions, newest first", ["Year", "Wrestler", "Weight"], "".join(tr(r) for r in HALL["district"][::-1]))

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
    coach_tbl = (f'<div class="table-wrap" tabindex="0"><table class="hall"><caption>Head coaches since 1945. Championship counts are tallied from the lists on this page.</caption>'
                 f'<thead><tr><th scope="col">Coach</th><th scope="col">Seasons</th><th scope="col">Years</th><th scope="col">Dual record</th><th scope="col">District XI</th><th scope="col">Regional</th><th scope="col">PIAA</th></tr></thead>'
                 f'<tbody>{coach_rows}</tbody><tfoot><tr><th scope="row">All-time</th><td></td><td>{TOTALS["seasons"]}</td><td>{tw}–{tl}–{tt}</td><td>{TOTALS["district"]}</td><td>{TOTALS["regional"]}</td><td>{TOTALS["state"]}</td></tr></tfoot></table></div>'
                 '<p class="fine">Joe Provini’s record is through the 2025–26 season.</p>')

    tabs = [("medals", "State Medalists", t_medals), ("regional", "Regional Champions", t_reg),
            ("district", "District XI Champions", t_dist), ("multi", "Multi-time honors", f'<div class="multi">{multi}</div>'),
            ("records", "Season records", f'<div class="records-grid">{records}</div>'), ("coaches", "Head coaches", coach_tbl)]
    tablist = "".join(f'<button type="button" role="tab" id="tab-{k}" aria-controls="panel-{k}" aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else " tabindex=\"-1\""}>{l}</button>'
                      for i, (k, l, _) in enumerate(tabs))
    panels = "".join(f'<div class="panel" role="tabpanel" id="panel-{k}" aria-labelledby="tab-{k}" tabindex="0"{"" if i == 0 else " hidden"}>{c}</div>'
                     for i, (k, _, c) in enumerate(tabs))
    open(os.path.join(ROOT, "assets", "data", "hall.json"), "w").write(json.dumps(hall_json(), separators=(",", ":")))
    body = f"""
{hall_wall_head(R, "Hall of Champions", "Every Konkrete Kid who has won a District XI, Northeast Regional, or PIAA title or medaled at the state tournament, from 1948 to today.")}
<section class="band" aria-labelledby="team-title">
  <div class="wrap">
    {section_head(f'<span id="team-title">{TOTALS["team_titles"]} PIAA team titles</span>', f'Northampton won the team title at the PIAA Class AAA championships seven times between 1993 and 2004. The program has also had at least one State Medalist every year since {TOTALS["streak"][0]}, {TOTALS["streak"][2]} straight seasons.')}
    <p class="wall-hint"><span aria-hidden="true">▶</span> Tap any banner for that season’s story, results and highlight video.</p>
    <ol class="team-banners" role="list">{"".join(f'<li class="tbanner has-photo">' + (picture(R, TEAM_PHOTOS[str(int(r["season"][:4]) + 1)], "(min-width: 900px) 15vw, 45vw", "tb-photo") if TEAM_PHOTOS.get(str(int(r["season"][:4]) + 1)) else f'<span class="tb-photo tb-ph"><img src="{R}assets/img/logo-192.png" alt="" width="96" height="96" loading="lazy"></span>') + f'<span class="t1">Northampton Wrestling</span><span class="t2">PIAA State Champions</span><span class="t3">AAA</span><a class="yr" href="{R}champions/team/{int(r["season"][:4]) + 1}/"><span class="visually-hidden">The </span>{e(r["season"])}<span class="visually-hidden"> team title season</span></a><span class="tb-more" aria-hidden="true">▶ Season &amp; video</span></li>' for r in TEAM_TITLES)}</ol>
  </div>
</section>
<section class="band dark wall-band" aria-labelledby="wall-title">
  <div class="wrap">
    {section_head(f'<span id="wall-title">{TOTALS["state"]} state titles</span>', "The banner wall, newest first.")}
    <p class="wall-hint on-dark"><span aria-hidden="true">▶</span> Tap any banner for that champion’s story and photos. ▶ means there’s state-final video.</p>
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
    <p class="fine">Missing or misspelled names? <a href="{SITE['links']['share_form']}" rel="noopener" target="_blank">Send a correction</a>. (We read everything but can’t reply individually.)</p>
  </div>
</section>
"""
    return page("champions/index.html", "Hall of Champions", "Northampton wrestling’s PIAA Champions, State Medalists, Regional and District XI Champions, season records, and head coaches since 1945.", body, "champions/", scripts=("site.js", "hall.js"), og_image="portrait-ballard-2026")


def season_phrases(facts, title):
    """Plain-English phrases from season_facts, e.g. '3 State Champions'."""
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
            out.append(f"{n} {a[:-1] if n == 1 else a}")
    if team:
        out.insert(1 if out and out[0].startswith(("PIAA", "1", "2", "3", "4", "5", "6", "7", "8", "9")) and "PIAA" in out[0] else 0,
                   " and ".join(team) + " team champions")
    return out


PAWR ={f'{x["season"][:4]}-{x["season"][7:]}': x for x in json.load(open(os.path.join(DATA, "hall", "pawrestling-seasons.json")))["seasons"]}
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


TEAM_SEASONS = load_toml("hall/team-seasons.toml")


def season_record(y, pw, d):
    """(record, league record) to show, or ("", ""). Detailed seasons use their own record and title seasons
    the team page's; otherwise PA-Wrestling's only when enough duals were captured to be the whole season."""
    if d and d.get("dual_record"):
        return d["dual_record"], ""
    ts = TEAM_SEASONS.get(str(y)) if y in TITLE_YEARS else None
    if ts and ts.get("record"):
        return ts["record"], ""
    if pw["record"] and len(pw["duals"]) >= 8:
        return pw["record"], pw["league_record"]
    return "", ""


LABEL_FIXES = [(r"Wresting", "Wrestling"), (r"NhSCA", "NHSCA"), (r"KonKrete", "Konkrete"), (r"DX1 AAA Team Duals", "District XI AAA Duals"),
               (r"District 11[- ]AAA", "District XI AAA"), (r"District 11\b", "District XI"), (r"\bSemi Finals\b", "Semifinals"),
               (r" - Semis\b", " (Semifinals)"), (r" Dual Meet$", "")]


def clean_label(s):
    """Tidy raw PA-Wrestling event labels for display."""
    for a, b in LABEL_FIXES:
        s = re.sub(a, b, s)
    return s


def season_facts(sid, y, pw, d):
    """Short facts for the index card and the season header. Only what the sources show."""
    f = []
    rec = season_record(y, pw, d)[0]
    if rec:
        f.append(("Dual record", rec))
    fin = dict(pw["finishes"])
    if y in TITLE_YEARS:
        f.append(("PIAA team", "State Champions"))
    elif fin.get("PIAA Championships"):
        f.append(("PIAA team", f'{fin["PIAA Championships"]} place'))
    for x in pw["duals"]:
        name = x["opponent"] + " " + x["event"]
        if ("Championship Final" in name or "(Finals)" in name or "(Championship)" in name) and ("PIAA" in name or "District" in name):
            f.append(("State duals" if "PIAA" in name else "District XI duals", "Champions" if x["result"].startswith("W") else "Runner-up"))
    for st, lab in (("District XI tournament", "District XI team"), ("Northeast Regional", "Regional team")):
        if fin.get(st) == "1st":
            f.append((lab, "Champions"))
    n_st = sum(int(r["year"]) == y for r in HALL["state"])
    n_md = n_st + sum(int(r["year"]) == y for r in HALL["medals"])
    if n_st:
        f.append(("State Champions", str(n_st)))
    if n_md > n_st:
        f.append(("State Medalists", str(n_md)))
    if not n_md:
        for k, lab in (("regional", "Regional Champions"), ("district", "District XI Champions")):
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
        cards.append(("PIAA Champions", [f'<a href="{R}champions/{slug(r["wrestler"])}/">{e(r["wrestler"])}</a><span>{e(r["weight"])}</span>' for r in st]))
    md = sorted((r for r in HALL["medals"] if int(r["year"]) == y), key=lambda r: int(r["place"]))
    if md:
        cards.append(("State Medalists", [f'{e(r["wrestler"])}<span>{PLACE[r["place"]]} · {e(r["weight"])}</span>' for r in md]))
    for k, lab in (("regional", "Northeast Regional Champions"), ("district", "District XI Champions")):
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


with open(os.path.join(DATA, "hall", "season-stories.json"), encoding="utf-8") as _f:
    SEASON_STORIES = json.load(_f)["seasons"]


def season_href(R, sid, y):
    """Where a season lives: the team-title page for PIAA team-title years, otherwise seasons/<id>/."""
    return f"{R}champions/team/{y}/" if y in TITLE_YEARS else f"{R}seasons/{sid}/"


def build_season_page(i, all_s):
    """One season, laid out the same way for every year (the layout the 2021-22+ seasons were built with)."""
    sid, label, y, pw, d = all_s[i]
    if y in TITLE_YEARS:
        # One page per season: a PIAA team-title season lives at champions/team/<year>/ (Joe, Oct. 21, 2026).
        redirect(f"seasons/{sid}/index.html", f"champions/team/{y}/")
        return None
    R = "../../"
    d = d or {}
    facts = season_facts(sid, y, pw, d or None)
    coach = season_coach(y)
    st = SEASON_STORIES.get(sid, {})
    headline = d.get("headline") or st.get("headline") or " · ".join(season_phrases(facts, y in TITLE_YEARS))
    parts = []
    if sid == CUR["id"]:
        parts.append(f'<div class="prose"><p>{d["dual_record"]} in duals, Parkland Duals champions, and 3rd at the District XI, Northeast Regional, and PIAA tournaments. Brayden Wenrich (114) and Gabe Ballard (152) won state titles, and Trey Wagner won a regional title at 139.</p>'
                     f'<p><a class="btn" href="{R}high-school/">Full 2025–26 recap</a></p></div>')
    if d.get("summary"):
        parts.append('<div class="prose cols">' + "".join(f"<p>{e(x)}</p>" for x in d["summary"]) + "</div>")
    elif st.get("story"):
        srcs = ([f'<a href="{e(st["source_url"])}" rel="noopener" target="_blank">Lehigh Valley Wrestling History</a>'] if st.get("source_url") else []) + ["PA-Wrestling", "Northampton’s banquet programs"]
        src = "Season facts from " + (", ".join(srcs[:-1]) + ", and " if len(srcs) > 2 else srcs[0] + " and ") + srcs[-1] + "."
        parts.append('<div class="prose cols season-story">' + "".join(f"<p>{e(x)}</p>" for x in st["story"]) + "</div>"
                     + f'<p class="fine story-src">{src} See something we got wrong? '
                     + f'<a href="{SITE["links"]["share_form"]}" rel="noopener" target="_blank">Send a correction</a>.</p>')
    # Team results list
    if d.get("team_finishes"):
        res = [("Dual meet record", d["dual_record"])] + [tuple(x) for x in d["team_finishes"]]
    else:
        rec_, lg_ = season_record(y, pw, d or None)
        res = ([("Dual meet record", rec_ + (f" ({lg_} league)" if lg_ else ""))] if rec_ else [])
        res += [tuple(x) for x in pw["finishes"]] + [tuple(x) for x in pw["tournaments"]]
    who = d.get("coaches") or (f"Head coach: {coach}" if coach else "")
    left = (f'<h2 class="sub">Team results</h2><ul class="results" role="list">{result_rows(res)}</ul>' if res
            else ("" if st.get("story") else '<h2 class="sub">Team results</h2><p class="arch-none">No stats available.</p>'))
    left += f'<p class="season-coaches">{e(who)}</p>' if who else ""
    if y in TITLE_YEARS:
        left += f'<p><a class="text-link" href="{R}champions/team/{y}/">The {label} PIAA team title season ›</a></p>'
    right = figure(R, d["team_photo"], "(min-width: 900px) 40vw, 100vw", "wide-fig") if d.get("team_photo") else ""
    duals_complete = bool(pw["record"]) and season_record(y, pw, d or None)[0] == pw["record"]
    if not right and pw["duals"]:
        right = (f'<h2 class="sub">{"Duals" if duals_complete else "Duals on record"}</h2><ul class="arch-duals" role="list">' + "".join(
            f'<li><span class="ad-date">{e(x["date"])}</span><span class="ad-opp">{e(clean_label(x["opponent"]))}'
            + (f' <small>{e(clean_label(x["event"]))}</small>' if x["event"] else "") + (' <small>league</small>' if x["league"] else "")
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
        tbl = f'<h2 class="sub">Postseason</h2>{postseason_table(post, label + " postseason results by wrestler", titles_only=not d.get("postseason"))}' if post else ""
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
        tail += f'<h2 class="sub">Junior high</h2><p>{e(". ".join(bits))}.' + (f" District Placewinners: {e(pwn)}." if pwn else "") + "</p>"
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
        parts.append('<details class="season-roster"><summary>' + (f'All {e(label)} duals' if duals_complete else f'{e(label)} duals on record') + '</summary><ul class="arch-duals" role="list">' + "".join(
            f'<li><span class="ad-date">{e(x["date"])}</span><span class="ad-opp">{e(clean_label(x["opponent"]))}'
            + (f' <small>{e(clean_label(x["event"]))}</small>' if x["event"] else "") + (' <small>league</small>' if x["league"] else "")
            + f'</span><b class="nw">{e(x["result"])}</b></li>' for x in pw["duals"]) + '</ul><p class="fine">Winner’s score first.</p></details>')
    sv = season_videos(sid, label)
    if sv:
        parts.append(f'<h2 class="sub">Season highlight video{"s" if len(SEASON_VIDEOS[sid]) > 1 else ""}</h2>{sv}')
    if d.get("gallery"):
        parts.append(f'<h2 class="sub">Photos</h2>{gallery(R, d["gallery"], "season-" + sid)}')

    newer = all_s[i - 1] if i > 0 else None
    older = all_s[i + 1] if i + 1 < len(all_s) else None
    nav = ('<nav class="season-nav" aria-label="More seasons">'
           + (f'<a href="{season_href("../../", older[0], older[2])}">‹ {older[1]}</a>' if older else "<span></span>")
           + '<a href="../">All seasons</a>'
           + (f'<a href="{season_href("../../", newer[0], newer[2])}">{newer[1]} ›</a>' if newer else "<span></span>") + "</nav>")
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
        card = (f'<a class="sc{" title" if title else ""}{" has-img" if thumb else ""}" href="{season_href(R, sid, y)}" id="{sid}">{thumb}<span class="sc-body">'
                f'<span class="sc-yr">{label}</span>'
                + ('<span class="sc-badge">PIAA team champions</span>' if title else "")
                + (f'<span class="sc-head">{e(d["headline"])}</span>' if d else (f'<span class="sc-head">{e(SEASON_STORIES[sid]["headline"])}</span>' if sid in SEASON_STORIES else ""))
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
{page_head(R, "Past Seasons", "Every season on record since 1946–47 (the program began in 1945–46). Pick a season for its results, champions, duals, and video.")}
<nav class="jump seasons-jump wrap" aria-label="Decades"><div class="jump-row">{jump}</div></nav>
{groups}
{redirect_js}
"""
    page("seasons/index.html", "Past Seasons", "Northampton wrestling season archive: results, State Medalists, and awards for every season.", body, "seasons/", og_image="team-2025")
    return [SITE["domain"] + "/seasons/"] + [SITE["domain"] + f"/seasons/{x[0]}/" for x in all_s if x[2] not in TITLE_YEARS]


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
    urls = [v2.build_home(), build_high_school(), build_schedule(), build_junior_high(), build_youth(), build_parent_guide()]
    if YOUTH_COACHES_LIVE:
        urls.append(build_youth_coaches())
    urls += [build_coaches(), build_champions(), build_trivia()] + build_seasons()
    urls += v2.build_all(sys.modules[__name__])
    build_404()
    # Old Wix addresses keep working
    redirect("schedule-1/index.html", "schedule/")
    redirect("copy-of-high-school/index.html", "seasons/2022-23/")
    redirect("copy-of-high-school-1/index.html", "seasons/2023-24/")
    redirect("coaches/index.html", "coaching-staff/")
    redirect("photos/index.html", "seasons/")  # Photos page retired (Joe, Oct. 2026): every photo lives on a season or other page
    if not YOUTH_COACHES_LIVE:
        redirect("youth/coaches/index.html", "youth/")  # paused: old links land on the Youth page
    # Sitemap: every built page (not redirect stubs), so new profiles and news posts are always included
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith(".") and x not in ("node_modules", "assets", "tools", "data")]
        if "index.html" in files:
            rel = os.path.relpath(d, ROOT)
            with open(os.path.join(d, "index.html"), encoding="utf-8") as fh:
                if 'http-equiv="refresh"' in fh.read(3000):
                    continue
            u = SITE["domain"] + "/" + ("" if rel == "." else rel.replace(os.sep, "/") + "/")
            if u not in urls:
                urls.append(u)
    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE['domain']}/sitemap.xml\n")
    print(f"built {len(urls)} pages")


if __name__ == "__main__":
    main()
