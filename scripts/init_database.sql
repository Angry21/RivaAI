-- Initialize RivaAI database with pgvector extension
-- This script sets up the core schema for the knowledge base

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create crops table
CREATE TABLE IF NOT EXISTS crops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    local_names JSONB,
    season VARCHAR(50),
    region VARCHAR(100),
    soil_requirements TEXT,
    water_requirements TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create chemicals table
CREATE TABLE IF NOT EXISTS chemicals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    safe_dosage_min FLOAT,
    safe_dosage_max FLOAT,
    unit VARCHAR(20),
    safety_warnings JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create schemes table (welfare/education)
CREATE TABLE IF NOT EXISTS schemes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL, -- 'welfare', 'education'
    local_names JSONB,
    eligibility_criteria JSONB,
    required_documents JSONB,
    application_process TEXT,
    contact_info JSONB,
    last_updated TIMESTAMP,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create crop-chemical relationships table
CREATE TABLE IF NOT EXISTS crop_chemical_relationships (
    id SERIAL PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id) ON DELETE CASCADE,
    chemical_id INTEGER REFERENCES chemicals(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50), -- 'SAFE_FOR', 'REQUIRES', 'AVOID'
    dosage_recommendation VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(crop_id, chemical_id, relationship_type)
);

-- Create crop weather requirements table
CREATE TABLE IF NOT EXISTS crop_weather_requirements (
    id SERIAL PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id) ON DELETE CASCADE,
    weather_condition VARCHAR(100),
    requirement_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vector search indexes using ivfflat
-- Note: These should be created after data is loaded for optimal performance
CREATE INDEX IF NOT EXISTS crops_embedding_idx ON crops USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chemicals_embedding_idx ON chemicals USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS schemes_embedding_idx ON schemes USING ivfflat (embedding vector_cosine_ops);

-- Create standard indexes for common queries
CREATE INDEX IF NOT EXISTS crops_name_idx ON crops(name);
CREATE INDEX IF NOT EXISTS chemicals_name_idx ON chemicals(name);
CREATE INDEX IF NOT EXISTS schemes_name_idx ON schemes(name);
CREATE INDEX IF NOT EXISTS schemes_domain_idx ON schemes(domain);
CREATE INDEX IF NOT EXISTS crop_chemical_crop_id_idx ON crop_chemical_relationships(crop_id);
CREATE INDEX IF NOT EXISTS crop_chemical_chemical_id_idx ON crop_chemical_relationships(chemical_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_crops_updated_at BEFORE UPDATE ON crops
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chemicals_updated_at BEFORE UPDATE ON chemicals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for Wheat (as per design document - start small)
INSERT INTO crops (name, local_names, season, region, soil_requirements, water_requirements)
VALUES (
    'Wheat',
    '{"hi": "गेहूं", "mr": "गहू", "te": "గోధుమ", "ta": "கோதுமை", "bn": "গম"}',
    'Rabi',
    'North India',
    'Well-drained loamy soil with pH 6.0-7.5',
    'Moderate water requirement, 4-5 irrigations during growing season'
) ON CONFLICT DO NOTHING;

-- Note: Embeddings will be populated by the application
-- Safety messages and additional data will be loaded separately

COMMENT ON TABLE crops IS 'Agricultural crop information with vector embeddings';
COMMENT ON TABLE chemicals IS 'Chemical (pesticide/fertilizer) information with safety limits';
COMMENT ON TABLE schemes IS 'Government welfare and education schemes';
COMMENT ON TABLE crop_chemical_relationships IS 'Graph relationships between crops and chemicals';
