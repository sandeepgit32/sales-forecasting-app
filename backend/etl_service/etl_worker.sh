#!/bin/bash
set -e

# Simple wrapper to run the ETL worker
python /app/etl_service/etl_worker.py
