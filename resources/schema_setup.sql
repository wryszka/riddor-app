-- RIDDOR Decision Support - Unity Catalog Schema Setup
-- Run this against the lr_serverless_aws_us_catalog catalog

CREATE SCHEMA IF NOT EXISTS lr_serverless_aws_us_catalog.riddor;

USE CATALOG lr_serverless_aws_us_catalog;
USE SCHEMA riddor;

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
  id STRING NOT NULL,
  reference STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  incident_date DATE NOT NULL,
  incident_type STRING NOT NULL COMMENT 'death, specified_injury, over_7_day, non_worker_hospital, occupational_disease, dangerous_occurrence, not_reportable',
  person_name STRING,
  person_type STRING COMMENT 'worker or non_worker',
  department STRING,
  location STRING,
  description STRING,
  injury_details STRING,
  ai_classification STRING COMMENT 'JSON blob of AI classification result',
  ai_reasoning STRING,
  manager_override STRING,
  status STRING NOT NULL COMMENT 'open, investigating, pending_report, submitted, closed',
  reporting_deadline DATE,
  hse_reference STRING,
  submitted_at TIMESTAMP,
  reporter_name STRING,
  reporter_email STRING,
  absence_days INT
)
USING DELTA
COMMENT 'RIDDOR incident records';

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
  id STRING NOT NULL,
  incident_id STRING NOT NULL,
  filename STRING NOT NULL,
  file_type STRING,
  upload_date TIMESTAMP NOT NULL,
  extracted_text STRING,
  storage_path STRING
)
USING DELTA
COMMENT 'Uploaded documents associated with incidents';

-- Chat history table
CREATE TABLE IF NOT EXISTS chat_history (
  id STRING NOT NULL,
  session_id STRING NOT NULL,
  role STRING NOT NULL COMMENT 'user or assistant',
  content STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  incident_id STRING COMMENT 'Optional reference to an incident being discussed'
)
USING DELTA
COMMENT 'AI chat conversation history';

-- Actions log table
CREATE TABLE IF NOT EXISTS actions_log (
  id STRING NOT NULL,
  incident_id STRING NOT NULL,
  action_type STRING NOT NULL COMMENT 'created, classified, updated, submitted, note, absence_update',
  description STRING,
  performed_by STRING,
  timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Audit trail of actions taken on incidents';
