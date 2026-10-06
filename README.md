# Northampton Wrestling website

The website for Northampton Wrestling, the Konkrete Kids: northamptonwrestling.org.

## How it works

The pages are generated from plain text files in `data/`:

| File | What it holds |
|---|---|
| `data/site.toml` | Contact info, social links, current season |
| `data/seasons.toml` | Results, awards, rosters, and seniors for each season |
| `data/coaches.toml` | Coaching staff bios and club officers |
| `data/stats-2025-26.csv` | Final varsity stats |
| `data/hall/*.csv` | Every District XI, Regional, and PIAA champion, state placewinners, season records, head coaches |
| `data/photos.toml` | Every photo, with its description, caption, and photographer credit |

After changing a data file, rebuild the pages:

```
python3 tools/build.py
```

To add or re-crop photos, list them in `data/photos.toml` and run `python3 tools/images.py --src <folder with originals>`.

Don't edit the generated HTML pages directly; the next build overwrites them.

## Fonts and credits

Anton, Inter, and Mr Dafoe are open-source fonts under the SIL Open Font License. Action photos marked with a credit are by Aaron Morekin.
