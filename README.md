# Recommend-It

A personal media-recommendation and rating database.  
**Recommend-It** uses a local **SQLite** database as the single source of truth for everything you rate or import — books, games, movies, shows, and music.

It’s designed to let you **record ratings from many sources**, combine them with your own opinions, and later **export clean Excel or JSON snapshots** for analysis or sharing.

---

## ✨ Core Features

- **SQLite-first design** — portable, file-based, no server required.
- **Flexible rating scales**:
  - ⭐ 1–5 stars  
  - ✅ thumbs up/down  
  - % percent or letter grades (extendable)
- **Confidence weighting** — vote counts from public sites boost trust scores automatically (`√votes`).
- **Multi-source imports** — record ratings from Goodreads, Itch.io, personal notes, etc.
- **Public Itch.io scraper** — fetches rating averages and counts straight from game pages.
- **Excel export** — one workbook, multiple tabs by media type (Games, Books, Movies, TV, Music).
- **JSON / CSV export** for scripting or dashboard tools.

---

## 📦 Quick Start

Create a new database and seed defaults:

```bash
python src/recommend-it.py init-db recommend-it.db
python src/recommend-it.py add-scale-defaults recommend-it.db
python src/recommend-it.py add-source recommend-it.db fred user
python src/recommend-it.py add-source recommend-it.db goodreads external
```

Rate something with a binary (thumb) scale:

```bash
python src/recommend-it.py rate-thumb recommend-it.db   --item "APICO" --media game --source fred --up
```

Fetch and store a live Itch.io rating:

```bash
python src/recommend-it.py fetch-itchio-rating recommend-it.db   --url "https://anuke.itch.io/mindustry"   --title "MINDUSTRY"
```

The above will normalize a 4.8-star average with 2,365 votes into a 96 % rating and compute confidence ≈ 48.6.

---

## 📊 Export Examples

### One tab per media type
```bash
python src/recommend-it.py export-xlsx recommend-it.db   --split-by-media   --out data/library-by-media.xlsx
```

### Custom tab order, include empty tabs
```bash
python src/recommend-it.py export-xlsx recommend-it.db   --split-by-media --tab-order game,book,movie,tv,music --include-empty-tabs   --out data/library-ordered.xlsx
```

### Filter to a single media (classic view)
```bash
python src/recommend-it.py export-xlsx recommend-it.db   --media game --platform web --min-itchio 80   --out data/web-games-80plus.xlsx
```

### Include a Ratings sheet
```bash
python src/recommend-it.py export-xlsx recommend-it.db   --split-by-media --include-ratings --source itchio   --out data/by-media-with-ratings.xlsx
```

Exports use **openpyxl**, so install it if missing:

```bash
pip install openpyxl
```

---

## 🧠 Schema Overview

| Table | Purpose |
|-------|----------|
| `media_type` | Master list of allowed media categories. |
| `item` | A book, game, movie, show, or song. |
| `platform` / `item_platform` | Where the item is available (web, Windows, etc.). |
| `rating_source` | Identifies who or what produced a rating (`fred`, `itchio`, `goodreads`). |
| `rating_scale` / `rating_scale_map` | Defines how raw ratings map to 0–100 %. |
| `item_rating` | Stores normalized ratings + vote counts and confidence. |
| `tag` / `item_tag` | Keyword tagging system (genres, moods, etc.). |
| `external_ref` | Links items to external sites or IDs (Itch.io URLs, Goodreads IDs, etc.). |

---

## 🧩 Extending

- Add new sources (Metacritic, IMDb, Steam) by mapping their rating scale to 0–100 %.
- Add new media types in `media_type`.
- Extend the Itch.io importer to read full tag listings or collections.
- Add a `recommend` command to surface top items by blended score.

---

## 🗂 Folder Layout

```
src/
 ├─ recommend-it.py     → main CLI entry point
 ├─ db.py               → database connection & schema loader
 ├─ ratings.py          → rating logic (scales, sources, confidence)
 ├─ itchio.py           → Itch.io importer/scraper
 ├─ export.py           → export helpers (CSV/JSON/XLSX)
 └─ schema.sql          → master schema (run once via init-db)
data/
 └─ sys/                → SQLite databases live here
```

---

## 🧰 Dependencies

- Python ≥ 3.9  
- Standard library: `sqlite3`, `argparse`, `json`, `csv`, `urllib`
- Optional:
  - `openpyxl` (for Excel export)

Install everything with:

```bash
pip install -r requirements.txt
```

---

## 🔒 Philosophy

Recommend-It keeps your data **local and auditable**.  
All imports, ratings, and exports run against a simple SQLite file—no cloud APIs, no tracking, no lock-in.

You own your ratings history, and every recommendation can be reproduced from one truth: the database.

---

_“The list will wait for you. The light will still be on when you return.”_