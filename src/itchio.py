import json
import xml.etree.ElementTree as ET
import json, re

from pathlib import Path
from urllib.request import urlopen, Request

from db import set_platforms, attach_tags, add_external_ref, connect
from ratings import add_scale_defaults, add_source
from ratings import ensure_item 

# ---------- Itch.io import ----------
def _norm_list(x):
    if x is None: return []
    if isinstance(x, (list, tuple)): return list(x)
    return [x]

def cmd_fetch_itchio_rating(args):
    conn = connect(args.db)
    # Ensure scales and the 'itchio' source exist
    add_scale_defaults(conn)
    add_source(conn, "itchio", "external")

    html = fetch_html(args.url)
    avg, count = extract_rating_from_html(html)
    if avg is None:
        print("No rating found on page (or game has no public ratings yet).")
        return

    # Normalize (0–5 stars) → percent, store with vote_count
    from ratings import add_rating_stars5
    title = args.title or args.url  # allow overriding if you already created the item
    item_id, percent, conf = add_rating_stars5(
        conn,
        item_title=title,
        media_code="game",
        source_name="itchio",
        stars=avg,
        votes=count,
        notes=f"Scraped from {args.url}"
    )
    print(f"Saved: item_id={item_id}, avg={avg}, votes={count}, percent={percent}, conf={conf:.2f}")

def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Recommend-It/1.0"})
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")

def extract_rating_from_html(html: str):
    """
    Returns (avg_stars: float|None, rating_count: int|None)
    Tries JSON-LD first, then falls back to simple heuristics.
    """
    # 1) JSON-LD blocks
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html, flags=re.S|re.I):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue

        # Some pages provide a single object, others a list
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            agg = obj.get("aggregateRating") if isinstance(obj, dict) else None
            if not isinstance(agg, dict):
                continue
            val = agg.get("ratingValue")
            cnt = agg.get("ratingCount") or agg.get("reviewCount")
            try:
                avg = float(val) if val is not None else None
                count = int(cnt) if cnt is not None else None
                if avg is not None:
                    return avg, count
            except Exception:
                pass

    # 2) Fallback: look for common rating text like “4.2 average (1,234 ratings)”
    # (Heuristic — safe to keep as a last resort)
    m = re.search(r'([0-5](?:\.\d)?)\s*(?:average|stars)[^0-9]{0,20}\(?([\d,]+)\s*ratings?\)?',
                  html, flags=re.I)
    if m:
        avg = float(m.group(1))
        count = int(m.group(2).replace(",", ""))
        return avg, count

    return None, None

def import_itchio_json_record(conn, rec: dict, *, web_only=False, free_only=False):
    # Try to read common fields present in API or exported JSON
    title = rec.get("title") or rec.get("name") or rec.get("game_title") or "(untitled)"
    desc = rec.get("short_text") or rec.get("description") or None
    url  = rec.get("url") or rec.get("game_url") or rec.get("cover_url") or None
    game_id = str(rec.get("id") or rec.get("game_id") or "")

    # platforms: Itch often lists like {"windows":true,"linux":false,"html5":true}
    plats = []
    p = rec.get("platforms") or {}
    if isinstance(p, dict):
        for k, v in p.items():
            if v:
                plats.append(k)
    else:
        plats = _norm_list(p)

    # tags: sometimes "tags": ["idle","cozy"], sometimes comma string
    tags = rec.get("tags") or rec.get("tag_names")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace("|", ",").split(",") if t.strip()]

    # price / free
    price = rec.get("price")  # could be 0, or string like "0", or cents in some dumps
    is_free = None
    if price is None:
        is_free = None
    else:
        try:
            is_free = float(price) == 0.0
        except Exception:
            is_free = str(price).strip() in ("0", "0.00", "free", "Free")

    # quick filters
    if web_only:
        platform_flags = set([s.lower() for s in plats])
        if "html5" not in platform_flags and "web" not in platform_flags and "browser" not in platform_flags:
            return 0
    if free_only and is_free is not None and is_free is False:
        return 0

    item_id = ensure_item(conn, title, "game", desc)
    set_platforms(conn, item_id, plats)
    attach_tags(conn, item_id, tags or [])
    add_external_ref(conn, item_id, source="itchio", external_id=game_id, url=url)
    return 1

def import_itchio_file(conn, path: str, *, web_only=False, free_only=False):
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    imported = 0

    # Try JSON first
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            imported += import_itchio_json_record(conn, data, web_only=web_only, free_only=free_only)
        elif isinstance(data, list):
            for rec in data:
                if isinstance(rec, dict):
                    imported += import_itchio_json_record(conn, rec, web_only=web_only, free_only=free_only)
        print(f"Imported {imported} from JSON")
        return
    except Exception:
        pass

    # Try RSS (XML)
    try:
        root = ET.fromstring(text)
        # Typical RSS: channel > item
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc  = (item.findtext("description") or "").strip()
            # tags sometimes in category nodes
            tags = [c.text.strip().lower() for c in item.findall("category") if c.text]
            # Heuristic: web playable is common in itch feed for HTML5; no direct flag, so let platforms empty
            rec = {"title": title, "url": link, "short_text": desc, "tags": tags}
            imported += import_itchio_json_record(conn, rec, web_only=web_only, free_only=free_only)
        print(f"Imported {imported} from RSS")
        return
    except Exception:
        pass

    print("Could not parse file as JSON or RSS. No rows imported.")
