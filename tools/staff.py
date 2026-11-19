"""Coaches' Room (staff/): the coaches' planner, weigh-ins, attendance, lifts, CrossFit times, matches.

Hidden page (noindex, not in the menu or sitemap). Coaches sign in with a passcode; the data
(names, weights, attendance) is NOT in this repo: it lives in a Google Sheet in Coach Provini's
Google account, reached through a Google Apps Script web app (Code.gs) that checks the passcode
on Google's side. Two passcodes: head coach (edits plans, roster, weight classes) and coach
(enters weigh-ins, attendance, lifts, CrossFit times, matches). Passcodes are on the Sheet's
"Passcodes" tab.

This repo is PUBLIC, so:
  - staff/index.html     the page code only (no data, no plans). Safe to read.
  - staff/season.json    the season (practice plans, clocks, first-run roster), ENCRYPTED
                         with the season key. The Apps Script hands the key to a signed-in coach.
  - tools/staff-source.json  the planner's source files, ENCRYPTED with the same key.
The season key is in Code.gs (Joe's Google account) and in the Claude project doc
"claude/Coaches Room keys (private).md". Never commit it, a passcode, or a plain copy of any
source file.

Commands (key from the STAFF_KEY environment variable):
  python3 tools/staff.py unpack DIR   decrypt the source files into DIR (outside the repo)
  python3 tools/staff.py pack DIR     re-encrypt edited source files from DIR
  python3 tools/staff.py build [DIR]  build staff/index.html + staff/season.json
Source files: app.html (the planner), season.py + master.py + master.txt (make data.json:
`cd DIR && python3 season.py`), data.json, seed.json (first-run roster), port.py + post.py
(turn app.html into the site page), seal.py, Code.gs.tpl (the Apps Script; Code.gs = this with
the key filled in), mock.js + t1.js + e2e.js (tests: `node DIR/t1.js`, mock server for e2e).
"""
import base64, hashlib, json, os, shutil, subprocess, sys, tempfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "tools", "staff-source.json")
OUT = os.path.join(ROOT, "staff")
# The Apps Script web app address (Deploy > Web app URL). Not a secret: the passcode protects the data.
API_URL = "__API_URL__"
FILES = ["app.html", "season.py", "master.py", "master.txt", "data.json", "seed.json", "port.py", "post.py",
         "seal.py", "Code.gs.tpl", "mock.js", "t1.js", "e2e.js"]


def key():
    k = os.environ.get("STAFF_KEY")
    if not k:
        sys.exit("Set STAFF_KEY first (in the Claude project doc 'Coaches Room keys (private)').")
    return base64.b64decode(k)


def unpack(d):
    b = json.load(open(BUNDLE))
    pt = AESGCM(key()).decrypt(base64.b64decode(b["iv"]), base64.b64decode(b["ct"]), None)
    files = json.loads(pt)
    os.makedirs(d, exist_ok=True)
    for name, text in files.items():
        open(os.path.join(d, name), "w", encoding="utf-8").write(text)
    print("unpacked", len(files), "files to", d)


def pack(d):
    files = {n: open(os.path.join(d, n), encoding="utf-8").read() for n in FILES if os.path.exists(os.path.join(d, n))}
    iv = os.urandom(12)
    ct = AESGCM(key()).encrypt(iv, json.dumps(files).encode(), None)
    json.dump({"v": 1, "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}, open(BUNDLE, "w"))
    print("packed", len(files), "files")


def build(d=None):
    tmp = None
    if not d:
        tmp = d = tempfile.mkdtemp()
        unpack(d)
    try:
        os.makedirs(OUT, exist_ok=True)
        env = dict(os.environ, SRC=os.path.join(d, "app.html"), OUT=os.path.join(OUT, "index.html"),
                   DATA=os.path.join(d, "data.json"))
        subprocess.run([sys.executable, os.path.join(d, "port.py")], check=True, env=env)
        subprocess.run([sys.executable, os.path.join(d, "post.py")], check=True, env=env)
        subprocess.run([sys.executable, os.path.join(d, "seal.py"), os.path.join(OUT, "season.json")], check=True, env=env)
        ver = hashlib.sha256(open(os.path.join(OUT, "season.json"), "rb").read()).hexdigest()[:10]
        p = os.path.join(OUT, "index.html")
        html = open(p, encoding="utf-8").read().replace("__API_URL__", API_URL).replace("__SEASON_VER__", ver)
        open(p, "w", encoding="utf-8").write(html)
        print("built staff/ (season", ver + ")")
    finally:
        if tmp:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "unpack" and len(sys.argv) == 3:
        unpack(sys.argv[2])
    elif cmd == "pack" and len(sys.argv) == 3:
        pack(sys.argv[2])
    elif cmd == "build":
        build(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        sys.exit(__doc__)
