import argparse
from db import init_db, connect
from ratings import add_scale_defaults, add_source, add_rating_stars5, add_rating_thumb
from itchio import cmd_fetch_itchio_rating, import_itchio_file
from export import _fetch_items_for_export, _fetch_ratings_ledger, _write_xlsx, _bucket_by_media

# ---- handlers ----
def cmd_init_db(args):
    init_db(args.db)
    print("db ready")

def cmd_add_scale_defaults(args):
    conn = connect(args.db)
    add_scale_defaults(conn)
    print("scales ready")

def cmd_add_source(args):
    conn = connect(args.db)
    add_source(conn, args.name, args.kind, args.weight, args.trust)
    print("source ready")

def cmd_rate5(args):
    conn = connect(args.db)
    print(add_rating_stars5(
        conn,
        item_title=args.item, media_code=args.media, source_name=args.source,
        stars=args.stars, votes=args.votes, notes=args.notes
    ))

def cmd_rate_thumb(args):
    if args.up and args.down:
        raise SystemExit("--up and --down are mutually exclusive")
    conn = connect(args.db)
    print(add_rating_thumb(
        conn,
        item_title=args.item, media_code=args.media, source_name=args.source,
        up=bool(args.up), votes=args.votes, notes=args.notes
    ))

def cmd_import_itchio(args):
    conn = connect(args.db)  # <-- make sure conn is defined here
    init_db(args.db)         # (optional if not already initialized)
    if not args.file and not args.rss:
        raise SystemExit("Provide --file (JSON) or --rss (XML)")
    path = args.file or args.rss
    import_itchio_file(conn, path, web_only=args.web_only, free_only=args.free_only)

def cmd_export_xlsx(args):
    conn = connect(args.db)

    # Pull items (optionally filtered by a single media/platform)
    items = _fetch_items_for_export(
        conn,
        media=args.media,              # note: if you set --split-by-media, consider leaving this None
        platform=args.platform,
        min_itchio=args.min_itchio,
        limit=args.limit
    )

    sheets = {}
    if args.split_by_media:
        # Optional explicit order via --tab-order=game,book,...
        order = [s.strip() for s in (args.tab_order or "").split(",") if s.strip()] or None
        sheets.update(_bucket_by_media(items, order=order, include_empty=args.include_empty_tabs))
    else:
        # Single 'Items' sheet (current behavior)
        sheets["Items"] = {"rows": items}

    # Optional Ratings sheet (unchanged behavior)
    if args.include_ratings:
        ratings = _fetch_ratings_ledger(
            conn,
            media=args.media if not args.split_by_media else None,  # if split, include all ratings
            source=args.source,
            since=args.since,
            limit=args.limit_ratings
        )
        sheets["Ratings"] = {"rows": ratings}

    # Write the workbook
    _write_xlsx(args.out, sheets)
    # Friendly summary
    tab_counts = ", ".join(f"{name}:{len(payload['rows'])}" for name, payload in sheets.items())
    print(f"wrote Excel → {args.out}  ({tab_counts})")

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    sp = sub.add_parser('init-db')
    sp.add_argument('db')
    sp.set_defaults(func=cmd_init_db)    

    sp = sub.add_parser('add-scale-defaults')
    sp.add_argument('db')
    sp.set_defaults(func=cmd_add_scale_defaults)

    sp = sub.add_parser('add-source')
    sp.add_argument('db')
    sp.add_argument('name')
    sp.add_argument('kind')
    sp.add_argument('--weight', type=float, default=1.0)
    sp.add_argument('--trust', type=float, default=1.0)
    sp.set_defaults(func=cmd_add_source)

    sp = sub.add_parser('rate5')
    sp.add_argument('db')
    sp.add_argument('--item', required=True)
    sp.add_argument('--media', required=True)
    sp.add_argument('--source', required=True)
    sp.add_argument('--stars', type=float, required=True)
    sp.add_argument('--votes', type=int)
    sp.add_argument('--notes')
    sp.set_defaults(func=cmd_rate5)

    sp = sub.add_parser("rate-thumb", help="Add a binary thumbs rating")
    sp.add_argument("db")
    sp.add_argument("--item", required=True)
    sp.add_argument("--media", required=True, choices=["game","book","movie","tv","music"])
    sp.add_argument("--source", required=True)
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--up", action="store_true", help="Thumbs up")
    group.add_argument("--down", action="store_true", help="Thumbs down")
    sp.add_argument("--votes", type=int, help="Number of ratings at the source")
    sp.add_argument("--notes")
    sp.set_defaults(func=lambda args: print(
        add_rating_thumb(
            connect(args.db),
            item_title=args.item,
            media_code=args.media,
            source_name=args.source,
            up=bool(args.up),
            votes=args.votes,
            notes=args.notes
        )
    ))

    sp = sub.add_parser("import-itchio")
    sp.add_argument("db")
    sp.add_argument("--file")
    sp.add_argument("--rss")
    sp.add_argument("--web-only", action="store_true")
    sp.add_argument("--free-only", action="store_true")
    sp.set_defaults(func=cmd_import_itchio)

    # in your argparse wiring:
    sp = sub.add_parser("fetch-itchio-rating", help="Scrape a single itch.io game page for rating/count")
    sp.add_argument("db")
    sp.add_argument("--url", required=True)
    sp.add_argument("--title", help="Optional item title override")
    sp.set_defaults(func=cmd_fetch_itchio_rating)

    sp = sub.add_parser("export-xlsx", help="Export items (and optional ratings) to Excel")
    sp.add_argument("db")
    sp.add_argument("--out", required=True, help="Output .xlsx path")
    sp.set_defaults(func=cmd_export_xlsx)

    # filters (same as before)
    sp.add_argument("--media", choices=["game","book","movie","tv","music"])
    sp.add_argument("--platform", help="Filter by platform, e.g. web")
    sp.add_argument("--min-itchio", type=int, help="Only items with Itch.io percent >= this")
    sp.add_argument("--limit", type=int, help="Max items")    

    # NEW: split tabs by media type
    sp.add_argument("--split-by-media", action="store_true", help="Create separate tabs per media type")
    sp.add_argument("--tab-order", help="Comma list of media codes to order tabs, e.g. 'game,book,movie,tv,music'")
    sp.add_argument("--include-empty-tabs", action="store_true", help="Include empty tabs if they appear in --tab-order")

    # Optional second sheet with detailed ratings (same as before)
    sp.add_argument("--include-ratings", action="store_true", help="Add a Ratings sheet")
    sp.add_argument("--source", help="Filter ratings by source (e.g., itchio, fred)")
    sp.add_argument("--since", help="Only ratings since this date (YYYY-MM-DD)")
    sp.add_argument("--limit-ratings", type=int, help="Max ratings rows")
    sp.set_defaults(func=cmd_export_xlsx)

    args = p.parse_args()
    return args.func(args) 

if __name__=='__main__':
    main()
