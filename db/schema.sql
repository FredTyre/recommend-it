PRAGMA foreign_keys = ON;

-- Media types
CREATE TABLE IF NOT EXISTS media_type (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL
);

INSERT OR IGNORE INTO media_type(code, description) VALUES
 ('game','Video game'),
 ('book','Book'),
 ('movie','Movie'),
 ('tv','TV show'),
 ('music','Music');

-- Items
CREATE TABLE IF NOT EXISTS item (
  id INTEGER PRIMARY KEY,
  media_code TEXT NOT NULL REFERENCES media_type(code),
  title TEXT NOT NULL,
  description TEXT,
  released_on TEXT,
  slug TEXT UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TRIGGER IF NOT EXISTS trg_item_updated_at
AFTER UPDATE ON item
FOR EACH ROW BEGIN
  UPDATE item SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Platforms
CREATE TABLE IF NOT EXISTS platform (
  code TEXT PRIMARY KEY,
  description TEXT NOT NULL
);
INSERT OR IGNORE INTO platform(code, description) VALUES
 ('web','Playable in browser'),
 ('windows','Windows'),
 ('linux','Linux'),
 ('mac','macOS'),
 ('android','Android'),
 ('ios','iOS');

CREATE TABLE IF NOT EXISTS item_platform (
  item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  platform_code TEXT NOT NULL REFERENCES platform(code),
  PRIMARY KEY(item_id, platform_code)
);

-- Ratings
CREATE TABLE IF NOT EXISTS rating_source (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK(kind IN ('user','external','critic','system')),
  weight REAL NOT NULL DEFAULT 1.0,
  trust  REAL NOT NULL DEFAULT 1.0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS rating_scale (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL CHECK(type IN ('continuous','ordinal','binary')),
  min_value REAL,
  max_value REAL,
  step REAL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS rating_scale_map (
  scale_id INTEGER NOT NULL REFERENCES rating_scale(id) ON DELETE CASCADE,
  raw_value TEXT NOT NULL,
  percent INTEGER NOT NULL CHECK (percent BETWEEN 0 AND 100),
  PRIMARY KEY (scale_id, raw_value)
);

CREATE TABLE IF NOT EXISTS item_rating (
  id INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  source_id INTEGER NOT NULL REFERENCES rating_source(id),
  scale_id INTEGER NOT NULL REFERENCES rating_scale(id),
  raw_value TEXT,
  value_num REAL,
  percent INTEGER NOT NULL CHECK (percent BETWEEN 0 AND 100),
  vote_count INTEGER,
  confidence REAL NOT NULL DEFAULT 1.0,
  rated_at TEXT NOT NULL DEFAULT (datetime('now')),
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_item_rating_item   ON item_rating(item_id);
CREATE INDEX IF NOT EXISTS idx_item_rating_source ON item_rating(source_id);

-- Tags + external refs (used by Itch importer & exports)
CREATE TABLE IF NOT EXISTS tag (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS item_tag (
  item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tag(id),
  PRIMARY KEY(item_id, tag_id)
);

-- External refs (no expressions in PK)
CREATE TABLE IF NOT EXISTS external_ref (
  item_id    INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  source     TEXT    NOT NULL,         -- 'itchio','goodreads', etc.
  external_id TEXT   NOT NULL DEFAULT '',  -- normalized empty string
  url         TEXT   NOT NULL DEFAULT '',  -- normalized empty string
  PRIMARY KEY (item_id, source, external_id, url)
);
