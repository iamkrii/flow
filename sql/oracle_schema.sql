-- Flow Oracle schema
-- Run this script in Oracle SQL Developer before starting the application.
-- The application generates UUID-style IDs in Python, but the users table
-- also keeps an Oracle default for direct inserts.

CREATE TABLE users (
    id VARCHAR2(32) DEFAULT LOWER(RAWTOHEX(SYS_GUID())) PRIMARY KEY,
    email VARCHAR2(255) NOT NULL UNIQUE,
    password_hash VARCHAR2(512) NOT NULL,
    name VARCHAR2(120),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE periods (
    id VARCHAR2(32) PRIMARY KEY,
    user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
    start_date DATE NOT NULL,
    end_date DATE,
    flow_level NUMBER(2),
    notes VARCHAR2(2000),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE symptoms (
    id VARCHAR2(32) PRIMARY KEY,
    user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
    log_date DATE NOT NULL,
    symptom VARCHAR2(80) NOT NULL,
    severity NUMBER(2),
    notes VARCHAR2(1000),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE moods (
    id VARCHAR2(32) PRIMARY KEY,
    user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
    log_date DATE NOT NULL,
    mood VARCHAR2(60) NOT NULL,
    energy NUMBER(2),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE daily_logs (
    id VARCHAR2(32) PRIMARY KEY,
    user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
    log_date DATE NOT NULL,
    weight_kg NUMBER(5,1),
    temperature_c NUMBER(4,1),
    discharge VARCHAR2(40),
    intercourse NUMBER(1),
    medication VARCHAR2(500),
    cramps NUMBER(2),
    notes VARCHAR2(2000),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE settings (
    user_id VARCHAR2(32) PRIMARY KEY REFERENCES users(id),
    avg_cycle_length NUMBER(3) DEFAULT 28,
    avg_period_length NUMBER(3) DEFAULT 5,
    luteal_phase_length NUMBER(3) DEFAULT 14,
    birth_control VARCHAR2(40),
    notifications_enabled NUMBER(1) DEFAULT 1
);

-- Useful indexes for user-scoped history and report queries.
CREATE INDEX ix_periods_user_start ON periods(user_id, start_date);
CREATE INDEX ix_symptoms_user_date ON symptoms(user_id, log_date);
CREATE INDEX ix_moods_user_date ON moods(user_id, log_date);
CREATE INDEX ix_daily_logs_user_date ON daily_logs(user_id, log_date);
