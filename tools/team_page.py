"""Build team/index.html, the password-locked team schedule, from tools/team-template.html.

The schedule itself lives in team/schedule.json, ENCRYPTED with the team password.
The coach edits it from the page (pencil button), which saves straight to this repo.
Never edit, rebuild or commit a plain-text copy of the schedule: the repo is public.
Run: python3 tools/team_page.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = open(os.path.join(ROOT, "tools", "team-template.html"), encoding="utf-8").read()
fonts = ('@font-face{font-family:"Anton";src:url("../assets/fonts/anton-400.woff2") format("woff2");font-display:swap}\n'
         '@font-face{font-family:"Inter";src:url("../assets/fonts/inter-var.woff2") format("woff2");font-weight:100 900;font-display:swap}')
head = ('<link rel="icon" href="../assets/img/icon-32.png">'
        '<link rel="apple-touch-icon" href="../assets/img/apple-touch-icon.png">')
html = (tpl.replace("__FONTS__", fonts).replace("__LOGO__", "../assets/img/logo-192.png")
        .replace("__PREVIEW__", "false").replace("__PAYLOAD__", "null").replace("__HEAD_LINKS__", head))
assert "__" not in html.split("<script>")[0].replace("__proto__", ""), "unfilled placeholder"
os.makedirs(os.path.join(ROOT, "team"), exist_ok=True)
open(os.path.join(ROOT, "team", "index.html"), "w", encoding="utf-8").write(html)
print("wrote team/index.html")
