-- app-download-estimator SQLite schema
-- Logical snapshot key: (platform, app_id, package, bundle, country)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS apps (
    app_key         TEXT PRIMARY KEY,
    platform        TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
    app_id          TEXT NOT NULL DEFAULT '',
    package         TEXT NOT NULL DEFAULT '',
    bundle          TEXT NOT NULL DEFAULT '',
    app_name        TEXT,
    created_at      TEXT NOT NULL DEFAULT '',
    updated_at      TEXT NOT NULL DEFAULT '',
    UNIQUE (platform, app_id, package, bundle)
);

CREATE TABLE IF NOT EXISTS rating_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date   TEXT NOT NULL,
    platform        TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
    app_id          TEXT NOT NULL DEFAULT '',
    package         TEXT NOT NULL DEFAULT '',
    bundle          TEXT NOT NULL DEFAULT '',
    country         TEXT NOT NULL,
    rating_count    INTEGER NOT NULL CHECK (rating_count >= 0),
    avg_rating      REAL CHECK (avg_rating IS NULL OR (avg_rating >= 0 AND avg_rating <= 5)),
    source_url      TEXT,
    source_quality  TEXT NOT NULL DEFAULT 'unknown'
        CHECK (source_quality IN ('unknown', 'country_specific', 'global_not_country')),
    collected_at    TEXT NOT NULL DEFAULT '',
    UNIQUE (snapshot_date, platform, app_id, package, bundle, country)
);

CREATE INDEX IF NOT EXISTS idx_rating_snapshots_lookup
    ON rating_snapshots (platform, app_id, package, bundle, country, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_rating_snapshots_date
    ON rating_snapshots (snapshot_date);

CREATE TABLE IF NOT EXISTS snapshot_quality_flags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id     INTEGER NOT NULL,
    flag_type       TEXT NOT NULL
        CHECK (flag_type IN (
            'negative_delta',
            'spike',
            'stale_gap',
            'global_not_country',
            'duplicate_country_values',
            'source_mismatch'
        )),
    note            TEXT,
    created_at      TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (snapshot_id) REFERENCES rating_snapshots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshot_quality_flags_snapshot
    ON snapshot_quality_flags (snapshot_id);

CREATE TABLE IF NOT EXISTS rating_velocity (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    platform                TEXT NOT NULL,
    app_id                  TEXT NOT NULL DEFAULT '',
    package                 TEXT NOT NULL DEFAULT '',
    bundle                  TEXT NOT NULL DEFAULT '',
    country                 TEXT NOT NULL,
    as_of_date              TEXT NOT NULL,
    previous_date           TEXT,
    current_rating_count    INTEGER,
    previous_rating_count   INTEGER,
    delta_ratings           INTEGER,
    snapshot_days           INTEGER,
    rating_velocity_daily   REAL,
    confidence              TEXT NOT NULL DEFAULT 'low'
        CHECK (confidence IN ('high', 'medium', 'low')),
    confidence_score        REAL,
    calc_method             TEXT NOT NULL DEFAULT 'adjacent'
        CHECK (calc_method IN ('adjacent', 'window_7d', 'window_14d')),
    created_at              TEXT NOT NULL DEFAULT '',
    UNIQUE (platform, app_id, package, bundle, country, as_of_date, calc_method)
);

CREATE INDEX IF NOT EXISTS idx_rating_velocity_lookup
    ON rating_velocity (platform, app_id, package, bundle, country, as_of_date);

CREATE TABLE IF NOT EXISTS market_benchmarks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    country         TEXT NOT NULL,
    app_id          TEXT NOT NULL DEFAULT '',
    app_name        TEXT,
    bundle          TEXT NOT NULL DEFAULT '',
    package         TEXT NOT NULL DEFAULT '',
    platform        TEXT NOT NULL DEFAULT '',
    category        TEXT,
    category_name   TEXT,
    chart_rank      INTEGER,
    downloads       INTEGER NOT NULL CHECK (downloads >= 0),
    report_start    TEXT,
    report_end      TEXT,
    source_file     TEXT,
    imported_at     TEXT NOT NULL DEFAULT '',
    UNIQUE (country, app_id, package, bundle, report_start, report_end)
);

CREATE INDEX IF NOT EXISTS idx_market_benchmark_lookup
    ON market_benchmarks (country, category_name, downloads);

CREATE INDEX IF NOT EXISTS idx_market_benchmark_app
    ON market_benchmarks (platform, app_id, package, bundle, country);

CREATE TABLE IF NOT EXISTS k_calibration (
    platform        TEXT NOT NULL,
    category        TEXT NOT NULL,
    country         TEXT NOT NULL,
    effective_k     REAL NOT NULL CHECK (effective_k > 0),
    sample_count    INTEGER NOT NULL DEFAULT 0,
    mape            REAL,
    p50_error       REAL,
    updated_at      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (platform, category, country)
);

CREATE TABLE IF NOT EXISTS download_estimates (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    estimate_date           TEXT NOT NULL,
    platform                TEXT NOT NULL,
    app_id                  TEXT NOT NULL DEFAULT '',
    package                 TEXT NOT NULL DEFAULT '',
    bundle                  TEXT NOT NULL DEFAULT '',
    country                 TEXT NOT NULL,
    category                TEXT,
    rank                    INTEGER,
    total_ratings           INTEGER,
    delta_ratings           REAL,
    rating_velocity_daily   REAL,
    k_base                  REAL,
    maturity_beta           REAL,
    regional_m              REAL,
    est_monthly_downloads   INTEGER,
    est_daily_downloads     INTEGER,
    confidence              TEXT,
    methodology             TEXT,
    benchmark_waterline     REAL,
    model_version           TEXT NOT NULL DEFAULT '1.0.0',
    created_at              TEXT NOT NULL DEFAULT '',
    UNIQUE (
        platform, app_id, package, bundle, country, estimate_date, model_version
    )
);

CREATE INDEX IF NOT EXISTS idx_download_estimates_lookup
    ON download_estimates (platform, app_id, package, bundle, country, estimate_date);

CREATE VIEW IF NOT EXISTS v_latest_snapshots AS
SELECT rs.*
FROM rating_snapshots rs
JOIN (
    SELECT
        platform,
        app_id,
        package,
        bundle,
        country,
        MAX(snapshot_date) AS max_date
    FROM rating_snapshots
    GROUP BY platform, app_id, package, bundle, country
) latest
  ON rs.platform = latest.platform
 AND rs.app_id = latest.app_id
 AND rs.package = latest.package
 AND rs.bundle = latest.bundle
 AND rs.country = latest.country
 AND rs.snapshot_date = latest.max_date;

CREATE VIEW IF NOT EXISTS v_latest_velocity AS
SELECT rv.*
FROM rating_velocity rv
JOIN (
    SELECT
        platform,
        app_id,
        package,
        bundle,
        country,
        calc_method,
        MAX(as_of_date) AS max_date
    FROM rating_velocity
    GROUP BY platform, app_id, package, bundle, country, calc_method
) latest
  ON rv.platform = latest.platform
 AND rv.app_id = latest.app_id
 AND rv.package = latest.package
 AND rv.bundle = latest.bundle
 AND rv.country = latest.country
 AND rv.calc_method = latest.calc_method
 AND rv.as_of_date = latest.max_date;
