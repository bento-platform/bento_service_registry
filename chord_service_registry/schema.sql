DROP TABLE IF EXISTS services;

CREATE TABLE services (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  url TEXT UNIQUE NOT NULL,
  service_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  contact_url TEXT NOT NULL,
  description TEXT NOT NULL,

  -- Metadata:
  chord_service_id TEXT UNIQUE, -- Unique gives it an index
  chord_data_service INTEGER CHECK (chord_data_service = 0 OR chord_data_service = 1),
  chord_manageable_tables INTEGER CHECK (chord_manageable_tables = 0 OR chord_manageable_tables = 1)
);
