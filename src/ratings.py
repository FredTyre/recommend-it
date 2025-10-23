import math
from sqlite3 import Connection

def add_scale_defaults(conn: Connection):
    conn.execute("INSERT OR IGNORE INTO rating_scale(name,type,min_value,max_value,step,notes) VALUES (?,?,?,?,?,?)", ('stars_5','continuous',0,5,0.5,'Half-star increments'))
    conn.execute("INSERT OR IGNORE INTO rating_scale(name,type,min_value,max_value,step,notes) VALUES (?,?,?,?,?,?)", ('thumb','binary',None,None,None,'Thumbs up/down'))
    thumb_id = conn.execute("SELECT id FROM rating_scale WHERE name='thumb'").fetchone()['id']
    conn.execute("INSERT OR IGNORE INTO rating_scale_map(scale_id,raw_value,percent) VALUES (?,?,?)", (thumb_id,'true',100))
    conn.execute("INSERT OR IGNORE INTO rating_scale_map(scale_id,raw_value,percent) VALUES (?,?,?)", (thumb_id,'false',0))
    conn.commit()

def add_source(conn: Connection, name: str, kind: str, weight: float=1.0, trust: float=1.0):
    conn.execute("INSERT OR IGNORE INTO rating_source(name,kind,weight,trust) VALUES (?,?,?,?)", (name, kind, weight, trust))
    conn.commit()

def ensure_item(conn: Connection, title: str, media_code: str):
    row = conn.execute("SELECT id FROM item WHERE title=? AND media_code=?", (title, media_code)).fetchone()
    if row: return row['id']
    cur = conn.execute("INSERT INTO item(media_code,title) VALUES(?,?)", (media_code,title))
    conn.commit()
    return cur.lastrowid

def normalize_percent_for_stars5(value_num: float) -> int:
    pct = int(round((value_num/5.0)*100))
    return max(0, min(100, pct))

def add_rating_stars5(conn: Connection, *, item_title: str, media_code: str, source_name: str, stars: float, votes: int=None, notes: str=None):
    item_id = ensure_item(conn, item_title, media_code)
    src = conn.execute("SELECT id FROM rating_source WHERE name=?", (source_name,)).fetchone()
    if not src: raise ValueError('source not found')
    scale = conn.execute("SELECT id FROM rating_scale WHERE name='stars_5'").fetchone()
    percent = normalize_percent_for_stars5(stars)
    conf = 1.0 if not votes else max(1.0, math.sqrt(max(0, votes)))
    conn.execute("INSERT INTO item_rating(item_id,source_id,scale_id,value_num,percent,vote_count,confidence,notes) VALUES (?,?,?,?,?,?,?,?)", (item_id, src['id'], scale['id'], stars, percent, votes, conf, notes))
    conn.commit()
    return item_id, percent, conf

def add_rating_thumb(conn, *, item_title: str, media_code: str, source_name: str,
                     up: bool, votes: int = None, notes: str = None):
    """Binary rating as thumbs up/down mapped to 100/0 percent."""
    
    item_id = ensure_item(conn, item_title, media_code)
    
    src = conn.execute("SELECT id FROM rating_source WHERE name=?", (source_name,)).fetchone()
    if not src:
        raise ValueError("source not found")
    
    scale = conn.execute("SELECT id FROM rating_scale WHERE name='thumb'").fetchone()
    raw = "true" if up else "false"
    
    percent = 100 if up else 0
    conf = 1.0 if not votes else max(1.0, math.sqrt(max(0, votes)))
    
    conn.execute(
        "INSERT INTO item_rating(item_id,source_id,scale_id,raw_value,percent,vote_count,confidence,notes) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (item_id, src["id"], scale["id"], raw, percent, votes, conf, notes)
    )
    conn.commit()

    return item_id, percent, conf
