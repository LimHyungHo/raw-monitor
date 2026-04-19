PRAGMA foreign_keys = ON;

-- =========================================================
-- users
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- monitoring_targets
-- One user can subscribe to multiple monitoring targets.
-- =========================================================
CREATE TABLE IF NOT EXISTS monitoring_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    document_name TEXT NOT NULL,
    document_id TEXT,
    source_org TEXT NOT NULL,
    notify_email TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_monitoring_targets_user_id
    ON monitoring_targets(user_id);

CREATE INDEX IF NOT EXISTS idx_monitoring_targets_document_id
    ON monitoring_targets(document_id);

-- =========================================================
-- monitoring_keywords
-- Keywords registered per target.
-- =========================================================
CREATE TABLE IF NOT EXISTS monitoring_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitoring_target_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    match_mode TEXT NOT NULL DEFAULT 'contains',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (monitoring_target_id) REFERENCES monitoring_targets(id)
);

CREATE INDEX IF NOT EXISTS idx_monitoring_keywords_target_id
    ON monitoring_keywords(monitoring_target_id);

-- =========================================================
-- source_documents
-- Canonical document master for all monitored sources.
-- law_api / rss / scrape / internal documents can all live here.
-- =========================================================
CREATE TABLE IF NOT EXISTS source_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    document_id TEXT NOT NULL,
    document_name TEXT NOT NULL,
    document_subtype TEXT,
    parent_document_id INTEGER,
    ministry_name TEXT,
    document_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_document_id) REFERENCES source_documents(id),
    UNIQUE (source_type, target_type, document_id)
);

CREATE INDEX IF NOT EXISTS idx_source_documents_parent_document_id
    ON source_documents(parent_document_id);

CREATE INDEX IF NOT EXISTS idx_source_documents_document_name
    ON source_documents(document_name);

-- =========================================================
-- document_versions
-- Stores raw and parsed snapshots of each document version.
-- =========================================================
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_document_id INTEGER NOT NULL,
    version_key TEXT NOT NULL,
    version_no INTEGER,
    effective_date TEXT,
    promulgation_date TEXT,
    announcement_no TEXT,
    revision_type TEXT,
    content_hash TEXT NOT NULL,
    raw_json TEXT,
    raw_text TEXT,
    parsed_json TEXT,
    is_current INTEGER NOT NULL DEFAULT 0,
    collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_document_id) REFERENCES source_documents(id),
    UNIQUE (source_document_id, version_key)
);

CREATE INDEX IF NOT EXISTS idx_document_versions_source_document_id
    ON document_versions(source_document_id);

CREATE INDEX IF NOT EXISTS idx_document_versions_effective_date
    ON document_versions(effective_date);

CREATE INDEX IF NOT EXISTS idx_document_versions_is_current
    ON document_versions(is_current);

CREATE INDEX IF NOT EXISTS idx_document_versions_content_hash
    ON document_versions(content_hash);

-- =========================================================
-- change_sets
-- Header of a comparison run between two versions.
-- =========================================================
CREATE TABLE IF NOT EXISTS change_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_document_id INTEGER NOT NULL,
    old_version_id INTEGER,
    new_version_id INTEGER NOT NULL,
    change_type TEXT NOT NULL,
    summary TEXT,
    keyword_hit_count INTEGER NOT NULL DEFAULT 0,
    has_structural_change INTEGER NOT NULL DEFAULT 0,
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_document_id) REFERENCES source_documents(id),
    FOREIGN KEY (old_version_id) REFERENCES document_versions(id),
    FOREIGN KEY (new_version_id) REFERENCES document_versions(id)
);

CREATE INDEX IF NOT EXISTS idx_change_sets_source_document_id
    ON change_sets(source_document_id);

CREATE INDEX IF NOT EXISTS idx_change_sets_new_version_id
    ON change_sets(new_version_id);

-- =========================================================
-- change_items
-- Detailed diff records at article / appendix / addenda level.
-- =========================================================
CREATE TABLE IF NOT EXISTS change_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_set_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    item_key TEXT NOT NULL,
    change_kind TEXT NOT NULL,
    old_text TEXT,
    new_text TEXT,
    diff_text TEXT,
    keyword_matched INTEGER NOT NULL DEFAULT 0,
    matched_keywords TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (change_set_id) REFERENCES change_sets(id)
);

CREATE INDEX IF NOT EXISTS idx_change_items_change_set_id
    ON change_items(change_set_id);

CREATE INDEX IF NOT EXISTS idx_change_items_item_key
    ON change_items(item_key);

-- =========================================================
-- alert_histories
-- Mail sending history per detected change.
-- =========================================================
CREATE TABLE IF NOT EXISTS alert_histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    monitoring_target_id INTEGER NOT NULL,
    change_set_id INTEGER NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    sent_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (monitoring_target_id) REFERENCES monitoring_targets(id),
    FOREIGN KEY (change_set_id) REFERENCES change_sets(id)
);

CREATE INDEX IF NOT EXISTS idx_alert_histories_user_id
    ON alert_histories(user_id);

CREATE INDEX IF NOT EXISTS idx_alert_histories_change_set_id
    ON alert_histories(change_set_id);

-- =========================================================
-- crawl_runs
-- Execution history for manual/scheduled runs.
-- =========================================================
CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    target_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_source_type
    ON crawl_runs(source_type);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at
    ON crawl_runs(started_at);
