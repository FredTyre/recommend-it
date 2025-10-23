# Recommend-It (scaffold)

SQLite-first scaffold for importing items and recording ratings from many sources.
Supports flexible scales (⭐ out of 5, percent, binary, letter grades) and **vote counts** with confidence weighting.

python src/recommend-it.py init-db recommend-it.db
python src/recommend-it.py add-scale-defaults recommend-it.db
python src/recommend-it.py add-source recommend-it.db fred user
python src/recommend-it.py add-source recommend-it.db goodreads external

python src/recommend-it.py rate-thumb recommend-it.db \
  --item "APICO" --media game --source fred --up

python src/recommend-it.py fetch-itchio-rating recommend-it.db \
  --url "https://anuke.itch.io/mindustry" \
  --title "MINDUSTRY"

# One tab per media; all items (best if you omit --media)
python src/recommend-it.py export-xlsx recommend-it.db \
  --split-by-media \
  --out data/library-by-media.xlsx

# Custom tab order, include empty tabs for consistency
python src/recommend-it.py export-xlsx recommend-it.db \
  --split-by-media --tab-order game,book,movie,tv,music --include-empty-tabs \
  --out data/library-ordered.xlsx

# Still possible to export a single media into one 'Items' tab (old behavior)
python src/recommend-it.py export-xlsx recommend-it.db \
  --media game --platform web --min-itchio 80 \
  --out data/web-games-80plus.xlsx

# Add a Ratings sheet too
python src/recommend-it.py export-xlsx recommend-it.db \
  --split-by-media --include-ratings --source itchio \
  --out data/by-media-with-ratings.xlsx