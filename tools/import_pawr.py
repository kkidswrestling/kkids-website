"""Turn PA-Wrestling season schedule captures into data/hall/pawrestling-seasons.json.

Input: one JSON file per season (as captured from
https://www.pa-wrestling.com/hs/teams/northampton/schedule.htm?seasonid=N), each
{"season": "1999-2000", "seasonid": 5, "season_record": "...", "league_record": "...",
 "rows": [{"date": ..., "opponent": ..., "result": ...}]}

Output keeps only facts the site shows: the season record, team placings at
postseason events, tournament placings, and dual scores. Placeholder link text
("results", "details", "TBA") is dropped. Nothing is inferred.

Usage: python3 tools/import_pawr.py <folder with season json files>
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACEHOLDER = {"", "results", "details", "tba", "result"}


def clean_record(s):
    m = re.search(r"(\d+)\s*-\s*(\d+)(?:\s*-\s*(\d+))?", s or "")
    if not m:
        return ""
    return "–".join(g for g in m.groups() if g)


def stage(name):
    n = name.lower()
    if "piaa" in n and "duals" in n:
        return "PIAA team duals"
    if "district" in n and "duals" in n:
        return "District XI duals"
    if "super regional" in n:
        return "Super Regional"
    if "regional" in n:
        return "Northeast Regional"
    if "district" in n:
        return "District XI tournament"
    if "piaa" in n:
        return "PIAA Championships"
    return None


def strip_markers(opp):
    """Remove the site's L / P / PS markers; report whether it was a league dual."""
    league = bool(re.search(r"\sL(\s|$)", opp))
    opp = re.sub(r"\s(L|P|PS)(?=\s|$)", "", opp)
    opp = re.sub(r"\s*\((\d+)(st|nd|rd|th) place\)", "", opp, flags=re.I)
    opp = re.sub(r"\s*-?\s*details\b", "", opp, flags=re.I)
    return re.sub(r"\s{2,}", " ", opp).strip(" -"), league


def event_name(opp):
    name, _ = strip_markers(opp)
    return re.split(r"\s+at\s+", name, maxsplit=1)[0].strip()


def convert(d):
    rows = d.get("rows", [])
    out = {"season": d["season"], "record": clean_record(d.get("season_record", "")),
           "league_record": clean_record(d.get("league_record", "")),
           "finishes": [], "tournaments": [], "duals": []}
    if out["league_record"] in ("0–0",):
        out["league_record"] = ""
    date, group = "", ""
    for r in rows:
        res = (r.get("result") or "").strip()
        opp = (r.get("opponent") or "").strip()
        if r.get("date"):
            date = r["date"].strip()
            group = ""
        is_place = re.match(r"^\d+(st|nd|rd|th) place$", res, re.I)
        is_score = re.match(r"^[WLT]\s*\d+\s*-\s*\d+", res)
        if res.lower() in PLACEHOLDER and not is_score:
            # header row of a pooled event / duals bracket: remember its name
            if r.get("date"):
                group = event_name(opp)
            continue
        if is_place:
            place = res.split()[0]
            st = stage(opp)
            if st:
                out["finishes"].append([st, place])
            else:
                out["tournaments"].append([event_name(opp), place])
        elif is_score:
            name, league = strip_markers(opp)
            score = re.sub(r"\s*-\s*", "–", res, count=1)
            score = re.sub(r"^([WLT])\s*", r"\1 ", score)
            ctx = group if (not r.get("date") and group) else ""
            out["duals"].append({"date": date, "opponent": name, "result": score,
                                 "league": league, "event": ctx})
    return out


def main(folder):
    seasons = []
    for f in sorted(os.listdir(folder)):
        if f.endswith(".json"):
            seasons.append(convert(json.load(open(os.path.join(folder, f)))))
    seasons.sort(key=lambda s: s["season"])
    dest = os.path.join(ROOT, "data", "hall", "pawrestling-seasons.json")
    json.dump({"source": "https://www.pa-wrestling.com/hs/teams/northampton/schedule.htm",
               "captured": "2026-10-08", "seasons": seasons}, open(dest, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {len(seasons)} seasons to {dest}")


if __name__ == "__main__":
    main(sys.argv[1])
