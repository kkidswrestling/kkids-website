"""HS Parents page (hs-parents/): password-locked family information page.

Everything on the page is private (Coach Provini's cell number in the honor code, the full
honor code, exact practice times), and this repo is PUBLIC. So nothing readable goes in:
  - hs-parents/content.json  the page itself, ENCRYPTED with the team password
  - tools/hs-parents-source.json  the page's source files, ENCRYPTED the same way
  - hs-parents/index.html  a public lock screen that unlocks content.json in the browser
Same scheme and salt as team/schedule.json (AES-GCM, PBKDF2-SHA256, capitals and spaces in
the password ignored), so a phone that unlocked the team schedule opens this page too.

Commands (the password comes from the TEAM_PASSWORD environment variable, never a file):
  python3 tools/hs_parents.py unpack DIR   decrypt the source files into DIR (outside the repo)
  python3 tools/hs_parents.py pack DIR     re-encrypt edited source files from DIR
  python3 tools/hs_parents.py build [DIR]  build hs-parents/ (from DIR, or from the packed source)
Source files: template.html (page), honor-code.md (full honor code), build.py (fills the
template; run as `python3 build.py site`), test.py / make_pdf.py (phone checks, optional).
If the team password changes (team page > More), unpack with the OLD password, then pack and
build with the NEW one, or the parent page stays locked with the old password.
"""
import base64, json, os, shutil, subprocess, sys, tempfile

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_BUNDLE = os.path.join(ROOT, "tools", "hs-parents-source.json")
OUT_DIR = os.path.join(ROOT, "hs-parents")
# Joe, Nov. 18, 2026: the page is public (no password). Set LOCKED = True to put the
# team-password lock back; the source bundle stays encrypted either way.
LOCKED = False
PARTS_DIR = os.path.join(ROOT, "data", "hs-parents")  # public page parts, wrapped by build.py (unlocked only)
SOURCE_FILES = ["template.html", "honor-code.md", "build.py", "test.py", "make_pdf.py"]


def key():
    pw = os.environ.get("TEAM_PASSWORD")
    if not pw:
        sys.exit("Set TEAM_PASSWORD first (the team schedule password).")
    team = json.load(open(os.path.join(ROOT, "team", "schedule.json")))
    salt, it = team["salt"], team["iter"]
    k = PBKDF2HMAC(hashes.SHA256(), 32, base64.b64decode(salt), it).derive("".join(pw.lower().split()).encode())
    # Check it really is the team password before writing anything.
    AESGCM(k).decrypt(base64.b64decode(team["iv"]), base64.b64decode(team["ct"]), None)
    return k, salt, it


def seal(obj, k, salt, it):
    iv = os.urandom(12)
    ct = AESGCM(k).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(), None)
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": it, "salt": salt,
            "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}


def open_sealed(p, k):
    return json.loads(AESGCM(k).decrypt(base64.b64decode(p["iv"]), base64.b64decode(p["ct"]), None))


def pack(src):
    k, salt, it = key()
    files = {n: open(os.path.join(src, n), encoding="utf-8").read() for n in SOURCE_FILES if os.path.exists(os.path.join(src, n))}
    json.dump(seal(files, k, salt, it), open(SRC_BUNDLE, "w"))
    print("packed", ", ".join(files), "->", os.path.relpath(SRC_BUNDLE, ROOT))


def unpack(dest):
    if os.path.abspath(dest).startswith(ROOT + os.sep):
        sys.exit("Unpack outside the repo (it's public).")
    k, _, _ = key()
    files = open_sealed(json.load(open(SRC_BUNDLE)), k)
    os.makedirs(dest, exist_ok=True)
    for n, t in files.items():
        open(os.path.join(dest, n), "w", encoding="utf-8").write(t)
    print("unpacked", ", ".join(files), "->", dest)


LOCK_CSS = """
.lock{min-height:100vh;min-height:100dvh;display:grid;place-items:center;padding:32px 20px;background:#141414;color:#f4f3f0;
  background-image:radial-gradient(ellipse at 50% 120%,rgba(242,106,27,.22),transparent 60%)}
.lock-box{width:100%;max-width:380px;text-align:center}
.lock-logo{width:96px;height:96px;margin:0 auto 18px;display:block}
.lock h1{font-family:"Anton",Impact,sans-serif;font-weight:400;text-transform:uppercase;letter-spacing:.02em;line-height:1;font-size:40px;margin:0 0 6px}
.lock p{color:#b9b5ad;margin:0 0 26px}
.lock form{display:grid;gap:12px}
.lock input{width:100%;padding:16px;border-radius:12px;border:2px solid #3a3b3f;background:#1f2023;color:#f4f3f0;font-size:18px;text-align:center}
.lock input:focus{border-color:#f26a1b;outline:none}
.lock button{min-height:48px;border-radius:12px;border:0;background:#f26a1b;color:#141414;font-weight:800;font-size:16px}
.lock button[disabled]{opacity:.55}
.lock .msg{min-height:24px;font-weight:700;color:#ffb38a;margin:4px 0 0}
.lock .fine{font-size:14px;margin-top:22px}
.lock a{color:#f4f3f0}
"""

LOCK_HTML = """<div id="lock" class="lock" hidden>
  <div class="lock-box">
    <img class="lock-logo" src="../assets/img/logo-192.png" alt="Northampton Konkrete Kids">
    <h1>HS Parents</h1>
    <p>Northampton Wrestling · for families of our high school wrestlers</p>
    <form id="lockForm" autocomplete="off">
      <input id="pw" type="password" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Team password" aria-label="Team password" required>
      <button id="unlockBtn" type="submit">Open</button>
      <p class="msg" id="lockMsg" role="alert"></p>
    </form>
    <p class="fine">Don’t have the password? Ask Coach Provini.<br><br><a href="../">Back to northamptonwrestling.org</a></p>
  </div>
</div>
<div id="app" hidden></div>
"""

LOADER = """<script>
(() => {
  "use strict";
  const KEY = "kk-team-key";
  const ls = {get(k){try{return localStorage.getItem(k)}catch(e){return null}}, set(k,v){try{localStorage.setItem(k,v)}catch(e){}}, del(k){try{localStorage.removeItem(k)}catch(e){}}};
  const te = new TextEncoder(), td = new TextDecoder();
  const $ = s => document.querySelector(s);
  function b64(u8){let s="";for(let i=0;i<u8.length;i+=0x8000)s+=String.fromCharCode.apply(null,u8.subarray(i,i+0x8000));return btoa(s)}
  function unb64(s){const b=atob(s);const u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u}
  const norm = pw => pw.toLowerCase().replace(/\\s+/g, "");
  async function derive(pw, salt, iter){
    const base = await crypto.subtle.importKey("raw", te.encode(norm(pw)), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey({name:"PBKDF2", salt:unb64(salt), iterations:iter, hash:"SHA-256"}, base, {name:"AES-GCM", length:256}, true, ["encrypt","decrypt"]);
  }
  async function decrypt(p, key){ return JSON.parse(td.decode(await crypto.subtle.decrypt({name:"AES-GCM", iv:unb64(p.iv)}, key, unb64(p.ct)))); }
  async function remember(key, salt){ const raw = new Uint8Array(await crypto.subtle.exportKey("raw", key)); ls.set(KEY, JSON.stringify({salt, k:b64(raw)})); }
  async function stored(salt){
    try { const s = JSON.parse(ls.get(KEY) || "null"); if (!s || s.salt !== salt) return null;
      return await crypto.subtle.importKey("raw", unb64(s.k), {name:"AES-GCM"}, true, ["encrypt","decrypt"]); } catch(e){ return null; }
  }
  let P = null;
  function show(d){
    $("#lock").hidden = true;
    const app = $("#app"); app.innerHTML = d.html; app.hidden = false;
    new Function(d.js)();
  }
  function lock(msg){ $("#lock").hidden = false; $("#lockMsg").textContent = msg || ""; }
  async function boot(){
    try { P = await (await fetch("content.json", {cache:"no-store"})).json(); }
    catch(e){ lock("Couldn’t load the page. Check your connection and refresh."); return; }
    const k = await stored(P.salt);
    if (k) { try { return show(await decrypt(P, k)); } catch(e){} }
    const had = ls.get(KEY);
    lock(had ? "The team password changed. Enter the new one." : "");
  }
  $("#lockForm").addEventListener("submit", async ev => {
    ev.preventDefault();
    const pw = $("#pw").value; if (!pw.trim() || !P) return;
    const btn = $("#unlockBtn"); btn.disabled = true; btn.textContent = "Opening…"; $("#lockMsg").textContent = "";
    try { const key = await derive(pw, P.salt, P.iter); const d = await decrypt(P, key); await remember(key, P.salt); $("#pw").value = ""; show(d); }
    catch(e){ $("#lockMsg").textContent = "That’s not the team password. Try again."; }
    btn.disabled = false; btn.textContent = "Open";
  });
  boot();
})();
</script>"""


def build(src=None):
    k, salt, it = key()
    tmp = tempfile.mkdtemp(prefix="hsp-")
    try:
        if src is None:
            files = open_sealed(json.load(open(SRC_BUNDLE)), k)
            for n, t in files.items():
                open(os.path.join(tmp, n), "w", encoding="utf-8").write(t)
        else:
            for n in SOURCE_FILES:
                if os.path.exists(os.path.join(src, n)):
                    shutil.copy(os.path.join(src, n), tmp)
        subprocess.run([sys.executable, "build.py", "site"], cwd=tmp, check=True, stdout=subprocess.DEVNULL)
        page = open(os.path.join(tmp, "site.html"), encoding="utf-8").read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not LOCKED:
        write_public_parts(page)
        old = os.path.join(OUT_DIR, "content.json")
        if os.path.exists(old):
            os.remove(old)
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py")], check=True, stdout=subprocess.DEVNULL)
        print("built hs-parents/index.html (public, inside the site's header and footer)")
        return
    for f in ("body.html", "page.css", "page.js"):
        if os.path.exists(os.path.join(PARTS_DIR, f)):
            os.remove(os.path.join(PARTS_DIR, f))
    head_end = page.index("</head>")
    body_start = page.index(">", page.index("<body")) + 1
    body_end = page.rindex("</body>")
    body = page[body_start:body_end]
    js_start = body.rindex("<script>")
    html, js = body[:js_start], body[js_start + 8:body.rindex("</script>")]
    assert "<script" not in html, "page body should have one script, at the end"
    head = page[:head_end].replace("<title>Family Information · Northampton Wrestling</title>", "<title>HS Parents · Northampton Wrestling</title>")
    https = ('<script>if (location.protocol === "http:" && !/^(localhost|127\\.0\\.0\\.1)$/.test(location.hostname)) '
             'location.replace("https:" + location.href.slice(5));</script>\n')
    head = head.replace("<head>", "<head>\n" + https, 1)
    shell = (head + f"<style>{LOCK_CSS}</style>\n</head>\n<body>\n" + LOCK_HTML + LOADER + "\n</body>\n</html>\n")
    # The public shell must carry none of the private page.
    for private in ("610-533", "honor code", "Honor code", "2:55"):
        assert private not in shell.split("<body>")[1], f"private text leaked into the shell: {private}"
    os.makedirs(OUT_DIR, exist_ok=True)
    open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8").write(shell)
    json.dump(seal({"html": html, "js": js}, k, salt, it), open(os.path.join(OUT_DIR, "content.json"), "w"))
    print("built hs-parents/index.html (public lock screen) and hs-parents/content.json (encrypted)")


# ---------- public (unlocked) page: fit it inside the site's own header, menu and footer ----------
import re as _re

def _split_rules(css):
    """Top-level CSS rules as (prelude, body) pairs; body is the text inside the braces."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{": depth += 1
            elif css[k] == "}": depth -= 1
            k += 1
        out.append((prelude, css[j + 1:k - 1]))
        i = k
    return out

def _scope_sel(sel):
    sel = sel.strip()
    if not sel:
        return sel
    m = _re.match(r"^(body|html)((?:[.:\[][^\s>+~]*)*)(.*)$", sel)
    if m:
        tag, quals, rest = m.groups()
        rest = rest.strip()
        if tag == "html" and not quals:
            return ".hsp" + ((" " + rest) if rest else "")
        if not quals:
            return ".hsp" + ((" " + rest) if rest else "")
        # body.viewing .topic -> body.viewing .hsp .topic ; body.sheet-open stays on body
        return "body" + quals + ((" .hsp " + rest) if rest else "")
    if sel.startswith(":root"):
        return ".hsp" + sel[5:]
    sel = _re.sub(r"(^|[\s>+~,(])main(?=$|[\s.:#\[>+~,{)])", r"\1.hsp-main", sel)
    return ".hsp " + sel

def scope_css(css):
    out = []
    for prelude, body in _split_rules(_re.sub(r"/\*.*?\*/", "", css, flags=_re.S)):
        if prelude.startswith("@media") or prelude.startswith("@supports"):
            out.append(prelude + "{" + scope_css(body) + "}")
        elif prelude.startswith("@"):
            out.append(prelude + "{" + body + "}")
        else:
            out.append(",".join(_scope_sel(x) for x in prelude.split(",")) + "{" + body + "}")
    return "\n".join(out)

# Undo the site stylesheet's element-wide rules inside the page (they come first, the page's own rules win).
RESET = """
.hsp{font-size:16px;line-height:1.5}
.hsp h1,.hsp h2,.hsp h3,.hsp h4{font-family:inherit;text-transform:none;letter-spacing:normal;line-height:1.2;margin:0;font-weight:700}
.hsp p{margin:0 0 .8em}
.hsp a{text-underline-offset:auto}
.hsp table{font-size:inherit}
.hsp th,.hsp td{padding:8px 6px;white-space:normal;border-bottom:1px solid var(--line)}
.hsp thead th{position:static;background:none;color:inherit;font-size:inherit}
.hsp tbody tr:hover{background:none}
.hsp details{border:0;padding:0}
.hsp summary{padding:0;font-weight:inherit}
.hsp summary:hover{color:inherit}
"""

AFTER = """
.hsp .hsp-main{max-width:var(--wrap);padding-left:var(--gutter);padding-right:var(--gutter)}
.hsp .jump{top:var(--hsp-top,71px)}
.hsp .sheet{z-index:200}
"""

TOP_JS = """(() => {
  const set = () => { const h = document.querySelector(".site-head"); if (h) document.documentElement.style.setProperty("--hsp-top", h.offsetHeight + "px"); };
  set(); addEventListener("resize", set);
})();
"""

def write_public_parts(page):
    css = page[page.index("<style>") + 7:page.index("</style>")]
    b0 = page.index(">", page.index("<body")) + 1
    body = page[b0:page.rindex("</body>")]
    js_at = body.rindex("<script>")
    html, js = body[:js_at], body[js_at + 8:body.rindex("</script>")]
    html = _re.sub(r'<header class="top">.*?</header>', "", html, count=1, flags=_re.S)
    html = _re.sub(r"<footer>.*?</footer>", "", html, count=1, flags=_re.S)
    html = _re.sub(r'\s*<div class="card intro">.*?</div>', "", html, count=1, flags=_re.S)  # the site page head says it
    html = html.replace("<main>", '<div class="hsp-main">', 1).replace("</main>", "</div>", 1)
    assert "<main" not in html and "<script" not in html
    os.makedirs(PARTS_DIR, exist_ok=True)
    open(os.path.join(PARTS_DIR, "body.html"), "w", encoding="utf-8").write('<div class="hsp">' + html + "</div>")
    open(os.path.join(PARTS_DIR, "page.css"), "w", encoding="utf-8").write(RESET + scope_css(css) + AFTER)
    open(os.path.join(PARTS_DIR, "page.js"), "w", encoding="utf-8").write(TOP_JS + js)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pack" and len(sys.argv) == 3: pack(sys.argv[2])
    elif cmd == "unpack" and len(sys.argv) == 3: unpack(sys.argv[2])
    elif cmd == "build": build(sys.argv[2] if len(sys.argv) == 3 else None)
    else: sys.exit(__doc__)
