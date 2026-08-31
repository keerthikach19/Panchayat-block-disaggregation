-- PostGIS Schema for Block-to-Panchayat Weather Downscaling System
-- Target: Maharashtra Footprint & Nashik Target District

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Panchayats / Administrative units
CREATE TABLE IF NOT EXISTS panchayats (
    panchayat_id VARCHAR(64) PRIMARY KEY,
    panchayat_name VARCHAR(128) NOT NULL,
    village_name VARCHAR(128),
    block_name VARCHAR(128) NOT NULL,
    district_name VARCHAR(128) NOT NULL,
    state_name VARCHAR(64) DEFAULT 'Maharashtra',
    area_sqkm DOUBLE PRECISION,
    geom GEOMETRY(Geometry, 4326)
);

CREATE INDEX IF NOT EXISTS idx_panchayats_geom ON panchayats USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_panchayats_district ON panchayats(district_name);
CREATE INDEX IF NOT EXISTS idx_panchayats_block ON panchayats(block_name);

-- 2. Panchayat Topographic & Environmental Covariates
CREATE TABLE IF NOT EXISTS panchayat_covariates (
    panchayat_id VARCHAR(64) PRIMARY KEY REFERENCES panchayats(panchayat_id) ON DELETE CASCADE,
    elevation_mean DOUBLE PRECISION,
    elevation_std DOUBLE PRECISION,
    elevation_min DOUBLE PRECISION,
    elevation_max DOUBLE PRECISION,
    slope_mean DOUBLE PRECISION,
    aspect_mean DOUBLE PRECISION,
    lulc_tree_pct DOUBLE PRECISION DEFAULT 0.0,
    lulc_shrub_pct DOUBLE PRECISION DEFAULT 0.0,
    lulc_grass_pct DOUBLE PRECISION DEFAULT 0.0,
    lulc_crop_pct DOUBLE PRECISION DEFAULT 0.0,
    lulc_urban_pct DOUBLE PRECISION DEFAULT 0.0,
    lulc_water_pct DOUBLE PRECISION DEFAULT 0.0,
    lulc_bare_pct DOUBLE PRECISION DEFAULT 0.0,
    dist_to_coast_km DOUBLE PRECISION,
    dist_to_water_km DOUBLE PRECISION,
    historical_rain_bias DOUBLE PRECISION DEFAULT 0.0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Weather Stations Metadata
CREATE TABLE IF NOT EXISTS stations (
    station_id VARCHAR(64) PRIMARY KEY,
    station_name VARCHAR(128) NOT NULL,
    district VARCHAR(128) NOT NULL,
    zone VARCHAR(64) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    elevation_m DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_stations_geom ON stations USING GIST(geom);

-- 4. Station Daily Observations
CREATE TABLE IF NOT EXISTS station_observations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(64) REFERENCES stations(station_id) ON DELETE CASCADE,
    obs_date DATE NOT NULL,
    rainfall_mm DOUBLE PRECISION,
    temp_max_c DOUBLE PRECISION,
    temp_min_c DOUBLE PRECISION,
    temp_mean_c DOUBLE PRECISION,
    rh_pct DOUBLE PRECISION,
    source VARCHAR(64),
    UNIQUE(station_id, obs_date)
);

CREATE INDEX IF NOT EXISTS idx_station_obs_date ON station_observations(obs_date);

-- 5. Downscaled Daily Forecasts & Disaggregation Results
CREATE TABLE IF NOT EXISTS downscaled_forecasts (
    forecast_id SERIAL PRIMARY KEY,
    panchayat_id VARCHAR(64) REFERENCES panchayats(panchayat_id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    block_rain_mean DOUBLE PRECISION,
    downscaled_rain_pred DOUBLE PRECISION,
    rain_ci_lower DOUBLE PRECISION,
    rain_ci_upper DOUBLE PRECISION,
    downscaled_tmax_pred DOUBLE PRECISION,
    downscaled_tmin_pred DOUBLE PRECISION,
    downscaled_rh_pred DOUBLE PRECISION,
    uncertainty_std DOUBLE PRECISION,
    confidence_level VARCHAR(32),
    layer_b_deviation DOUBLE PRECISION,
    layer_c_residual DOUBLE PRECISION,
    dominant_factor VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(panchayat_id, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_forecast_date ON downscaled_forecasts(forecast_date);

-- 6. GKMS SOP Agro-Meteorological Advisories
CREATE TABLE IF NOT EXISTS advisories (
    advisory_id SERIAL PRIMARY KEY,
    panchayat_id VARCHAR(64) REFERENCES panchayats(panchayat_id) ON DELETE CASCADE,
    issue_date DATE NOT NULL,
    valid_until DATE NOT NULL,
    dominant_crop VARCHAR(64) NOT NULL,
    crop_stage VARCHAR(64) NOT NULL,
    weather_summary_en TEXT NOT NULL,
    weather_summary_mr TEXT NOT NULL,
    agromet_advisory_en TEXT NOT NULL,
    agromet_advisory_mr TEXT NOT NULL,
    spray_recommendation TEXT,
    irrigation_advice TEXT,
    disease_pest_warning TEXT,
    alert_level VARCHAR(32) DEFAULT 'NORMAL', -- 'NORMAL', 'ADVISORY', 'WARNING', 'SEVERE'
    status VARCHAR(32) DEFAULT 'DRAFT',       -- 'DRAFT', 'REVIEWED', 'APPROVED', 'SENT'
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(panchayat_id, issue_date, dominant_crop)
);

-- 7. DAMU Officer Review & MLOps Feedback Log Table
CREATE TABLE IF NOT EXISTS officer_feedback_log (
    log_id SERIAL PRIMARY KEY,
    advisory_id INTEGER REFERENCES advisories(advisory_id) ON DELETE CASCADE,
    officer_id VARCHAR(64) NOT NULL,
    panchayat_id VARCHAR(64) NOT NULL,
    field_modified VARCHAR(64) NOT NULL,
    original_value TEXT,
    modified_value TEXT,
    edit_reason TEXT,
    action_type VARCHAR(32) NOT NULL, -- 'EDIT_ADVISORY', 'OVERRIDE_FORECAST', 'APPROVE', 'REJECT'
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_advisory ON officer_feedback_log(advisory_id);
