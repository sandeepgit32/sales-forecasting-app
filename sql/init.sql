-- init.sql: create database and tables for the timeseries forecasting app

CREATE DATABASE IF NOT EXISTS timeseries_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE timeseries_db;

-- Upload metadata
CREATE TABLE IF NOT EXISTS upload_metadata (
    batch_num VARCHAR(100) PRIMARY KEY,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    num_total_rows INT DEFAULT 0,
    num_missing_rows INT DEFAULT 0,
    num_imputed_rows INT DEFAULT 0,
    num_inserted_rows INT DEFAULT 0,
    num_updated_rows INT DEFAULT 0,
    status ENUM('uploaded','processing','completed','failed') DEFAULT 'uploaded',
    error_log TEXT,
    INDEX idx_file_hash (file_hash),
    INDEX idx_status (status),
    INDEX idx_uploaded_at (uploaded_at)
) ENGINE=InnoDB;

-- Invoice/Sales Data Table (cleaned data with composite PK)
CREATE TABLE IF NOT EXISTS invoice_data (
    date DATE NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    sales DECIMAL(12,2) NOT NULL,
    is_imputed BOOLEAN DEFAULT FALSE,
    batch_num VARCHAR(100) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    PRIMARY KEY (date, product_id, category),
    INDEX idx_date (date),
    INDEX idx_category (category),
    INDEX idx_batch (batch_num)
) ENGINE=InnoDB;

-- Forecast Data Table (category-wise only)
CREATE TABLE IF NOT EXISTS forecast_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    forecast_date DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    model_type ENUM('prophet','sarimax','holt_winters') NOT NULL,
    forecast_value DECIMAL(12,2) NOT NULL,
    lower_bound DECIMAL(12,2),
    upper_bound DECIMAL(12,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    batch_num VARCHAR(100),
    UNIQUE KEY unique_forecast (forecast_date, category, model_type),
    INDEX idx_forecast_date (forecast_date),
    INDEX idx_model (model_type),
    INDEX idx_category (category)
) ENGINE=InnoDB;
