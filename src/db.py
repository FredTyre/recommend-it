import sqlite3
from pathlib import Path
SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'db' / 'schema.sql'
STORAGE_DIR = Path(__file__).resolve().parents[1] / 'data' / 'sys'

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(STORAGE_DIR / db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = NORMAL;')
    return conn

def init_db(db_path: str):
    conn = connect(STORAGE_DIR / db_path)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    conn.close()

# ---------- Items / platforms / tags ----------
def ensure_item(conn, title: str, media_code: str, description: str=None) -> int:
    row = conn.execute("SELECT id FROM item WHERE title=? AND media_code=?", (title, media_code)).fetchone()
    if row:
        if description:
            conn.execute("UPDATE item SET description=COALESCE(description, ?) WHERE id=?", (description, row["id"]))
            conn.commit()
        return row["id"]
    cur = conn.execute("INSERT INTO item(media_code,title,description) VALUES(?,?,?)", (media_code, title, description))
    conn.commit()
    return cur.lastrowid

def set_platforms(conn, item_id: int, plat_list):
    codes = set()
    for raw in plat_list or []:
        s = str(raw).lower()
        if s in ("web","html5","browser","playable in browser"): codes.add("web")
        elif s in ("win","windows"): codes.add("windows")
        elif s in ("linux","gnu/linux"): codes.add("linux")
        elif s in ("mac","macos","osx"): codes.add("mac")
        elif s=="android": codes.add("android")
        elif s=="ios": codes.add("ios")
    for code in codes:
        conn.execute("INSERT OR IGNORE INTO item_platform(item_id,platform_code) VALUES (?,?)", (item_id, code))
    conn.commit()

def ensure_tag(conn, name: str) -> int:
    row = conn.execute("SELECT id FROM tag WHERE name=?", (name,)).fetchone()
    if row: return row["id"]
    cur = conn.execute("INSERT INTO tag(name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid

def attach_tags(conn, item_id: int, tags):
    if not tags: return
    for t in tags:
        name = str(t).strip().lower()
        if not name: continue
        tid = ensure_tag(conn, name)
        conn.execute("INSERT OR IGNORE INTO item_tag(item_id,tag_id) VALUES (?,?)", (item_id, tid))
    conn.commit()

def add_external_ref(conn, item_id: int, source: str, external_id: str=None, url: str=None):
    conn.execute(
        "INSERT OR IGNORE INTO external_ref(item_id,source,external_id,url) VALUES (?,?,?,?)",
        (item_id, source, external_id, url)
    )
    conn.commit()

def _dict_rows(cur):
    cols = [c[0] for c in cur.description]
    for row in cur.fetchall():
        yield {k: row[i] for i, k in enumerate(cols)}

def _fetch_items_for_export(conn, *, media=None, platform=None, min_itchio=None, limit=None):
    # latest itchio & latest fred via correlated subqueries (portable)
    q = """
    WITH plats AS (
      SELECT item_id, GROUP_CONCAT(DISTINCT platform_code) AS platforms
      FROM item_platform GROUP BY item_id
    ),
    tags AS (
      SELECT it.item_id, GROUP_CONCAT(DISTINCT t.name) AS tags
      FROM item_tag it JOIN tag t ON t.id = it.tag_id
      GROUP BY it.item_id
    ),
    latest_itch AS (
      SELECT r.*
      FROM item_rating r
      JOIN rating_source s ON s.id = r.source_id AND s.name = 'itchio'
      WHERE r.rated_at = (
        SELECT MAX(r2.rated_at)
        FROM item_rating r2
        JOIN rating_source s2 ON s2.id = r2.source_id AND s2.name = 'itchio'
        WHERE r2.item_id = r.item_id
      )
    ),
    latest_me AS (
      SELECT r.*
      FROM item_rating r
      JOIN rating_source s ON s.id = r.source_id AND s.name = 'fred'
      WHERE r.rated_at = (
        SELECT MAX(r2.rated_at)
        FROM item_rating r2
        JOIN rating_source s2 ON s2.id = r2.source_id AND s2.name = 'fred'
        WHERE r2.item_id = r.item_id
      )
    )
    SELECT
      i.id, i.title, i.media_code,
      COALESCE(p.platforms, '') AS platforms,
      COALESCE(g.tags, '') AS tags,
      li.percent AS itchio_percent,
      li.vote_count AS itchio_votes,
      li.rated_at AS itchio_rated_at,
      lm.percent AS my_percent,
      lm.rated_at AS my_rated_at
    FROM item i
    LEFT JOIN plats p ON p.item_id = i.id
    LEFT JOIN tags  g ON g.item_id = i.id
    LEFT JOIN latest_itch li ON li.item_id = i.id
    LEFT JOIN latest_me   lm ON lm.item_id = i.id
    WHERE 1=1
      AND (? IS NULL OR i.media_code = ?)
      AND (? IS NULL OR EXISTS (
          SELECT 1 FROM item_platform ip
          WHERE ip.item_id = i.id AND ip.platform_code = ?
      ))
      AND (? IS NULL OR (li.percent IS NOT NULL AND li.percent >= ?))
    ORDER BY COALESCE(lm.percent, li.percent) DESC, i.title ASC
    LIMIT COALESCE(?, 1000000)
    """
    params = (media, media, platform, platform, min_itchio, min_itchio, limit)
    cur = conn.execute(q, params)
    return list(_dict_rows(cur))

def _fetch_ratings_ledger(conn, *, media=None, source=None, since=None, limit=None):
    q = """
    SELECT i.id AS item_id, i.title, i.media_code,
           s.name AS source, r.scale_id, r.raw_value, r.value_num,
           r.percent, r.vote_count, r.confidence, r.rated_at
    FROM item_rating r
    JOIN item i ON i.id = r.item_id
    JOIN rating_source s ON s.id = r.source_id
    WHERE 1=1
      AND (? IS NULL OR i.media_code = ?)
      AND (? IS NULL OR s.name = ?)
      AND (? IS NULL OR r.rated_at >= ?)
    ORDER BY r.rated_at DESC, i.title ASC
    LIMIT COALESCE(?, 1000000)
    """
    params = (media, media, source, source, since, since, limit)
    cur = conn.execute(q, params)
    return list(_dict_rows(cur))
