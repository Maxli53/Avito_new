-- SQLite Schema for Snowmobile Reconciliation System

-- Price Lists Table
CREATE TABLE IF NOT EXISTS price_lists (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    brand TEXT NOT NULL,
    market TEXT NOT NULL,
    model_year INTEGER NOT NULL,
    total_entries INTEGER DEFAULT 0,
    processed_entries INTEGER DEFAULT 0,
    failed_entries INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    uploaded_at TEXT,
    processed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Price Entries Table
CREATE TABLE IF NOT EXISTS price_entries (
    id TEXT PRIMARY KEY,
    price_list_id TEXT NOT NULL,
    model_code TEXT NOT NULL,
    malli TEXT,
    paketti TEXT,
    moottori TEXT,
    telamatto TEXT,
    kaynnistin TEXT,
    mittaristo TEXT,
    kevatoptiot TEXT,
    vari TEXT,
    price REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    market TEXT NOT NULL,
    brand TEXT NOT NULL,
    model_year INTEGER NOT NULL,
    catalog_lookup_key TEXT NOT NULL,
    status TEXT DEFAULT 'extracted',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (price_list_id) REFERENCES price_lists(id)
);

-- Catalogs Table
CREATE TABLE IF NOT EXISTS catalogs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    brand TEXT NOT NULL,
    market TEXT NOT NULL,
    model_year INTEGER NOT NULL,
    total_models INTEGER DEFAULT 0,
    processed_models INTEGER DEFAULT 0,
    failed_models INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    uploaded_at TEXT,
    processed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Base Models Catalog Table
CREATE TABLE IF NOT EXISTS base_models_catalog (
    id TEXT PRIMARY KEY,
    catalog_id TEXT NOT NULL,
    model_code TEXT NOT NULL,
    malli TEXT,
    teho TEXT,
    iskutilavuus TEXT,
    sylinterit TEXT,
    kaynnistin TEXT,
    jarrutusteho TEXT,
    pakoputki TEXT,
    ajovalo TEXT,
    tuulisuoja TEXT,
    nakymametodiikka TEXT,
    kahvat TEXT,
    etulokasuoja TEXT,
    jousitus TEXT,
    tela TEXT,
    sukset TEXT,
    runkopituus REAL,
    kokonaisleveys REAL,
    kokonaiskorkeus REAL,
    telapituus REAL,
    suksijarivivali REAL,
    kuivapaino REAL,
    polttoainesailion_tilavuus REAL,
    status TEXT DEFAULT 'extracted',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (catalog_id) REFERENCES catalogs(id)
);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    price_entry_id TEXT NOT NULL,
    base_model_id TEXT,
    final_model_code TEXT NOT NULL,
    final_malli TEXT,
    final_price REAL NOT NULL,
    final_currency TEXT DEFAULT 'EUR',
    final_specifications TEXT, -- JSON
    final_features TEXT, -- JSON
    market TEXT NOT NULL,
    brand TEXT NOT NULL,
    model_year INTEGER NOT NULL,
    matching_confidence REAL,
    validation_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (price_entry_id) REFERENCES price_entries(id),
    FOREIGN KEY (base_model_id) REFERENCES base_models_catalog(id)
);

-- Processing Jobs Table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    input_params TEXT, -- JSON
    result_summary TEXT, -- JSON
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_price_entries_price_list_id ON price_entries(price_list_id);
CREATE INDEX IF NOT EXISTS idx_price_entries_model_code ON price_entries(model_code);
CREATE INDEX IF NOT EXISTS idx_price_entries_catalog_lookup_key ON price_entries(catalog_lookup_key);

CREATE INDEX IF NOT EXISTS idx_base_models_catalog_id ON base_models_catalog(catalog_id);
CREATE INDEX IF NOT EXISTS idx_base_models_model_code ON base_models_catalog(model_code);

CREATE INDEX IF NOT EXISTS idx_products_price_entry_id ON products(price_entry_id);
CREATE INDEX IF NOT EXISTS idx_products_base_model_id ON products(base_model_id);
CREATE INDEX IF NOT EXISTS idx_products_final_model_code ON products(final_model_code);