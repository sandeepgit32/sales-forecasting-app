import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import time
from datetime import timedelta
import redis
import pandas as pd
from sqlalchemy import text
from common.db import engine, SessionLocal

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
HORIZON = int(os.getenv('FORECAST_HORIZON_DAYS', '30'))

# Wait for services to be ready
def wait_for_services():
    max_retries = 30
    for i in range(max_retries):
        try:
            r_test = redis.from_url(REDIS_URL)
            r_test.ping()
            print("Redis connection successful")
            
            db_test = SessionLocal()
            db_test.execute(text("SELECT 1"))
            db_test.close()
            print("Database connection successful")
            return True
        except Exception as e:
            print(f"Waiting for services... ({i+1}/{max_retries}): {e}")
            time.sleep(2)
    raise Exception("Services not available after retries")

wait_for_services()

r = redis.from_url(REDIS_URL)
DB = SessionLocal()

def process_batch(batch_num):
    # Find distinct categories updated in this batch
    res = DB.execute(text('SELECT DISTINCT category FROM invoice_data WHERE batch_num = :batch'), {'batch': batch_num})
    categories = [row[0] for row in res]
    print(f"Forecasting for batch {batch_num}, categories: {categories}")

    for cat in categories:
        # Use separate connection for read
        df = pd.read_sql(
            text('SELECT `date`, SUM(sales) as sales FROM invoice_data WHERE category = :cat GROUP BY `date` ORDER BY `date`'),
            engine,
            params={'cat': cat}
        )
        if df.empty:
            continue
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        # Simple baseline forecast: mean of last 7 days
        last_vals = df['sales'].tail(7)
        baseline = float(last_vals.mean()) if not last_vals.empty else float(df['sales'].mean())

        forecasts = []
        last_date = df.index.max()
        for i in range(1, HORIZON+1):
            fdate = (last_date + timedelta(days=i)).date()
            # same baseline for all models for now
            for model in ('prophet','sarimax','holt_winters'):
                forecasts.append({'forecast_date': fdate, 'category': cat, 'model_type': model, 'forecast_value': round(baseline, 2), 'lower_bound': None, 'upper_bound': None})

        # upsert forecasts with new connection and transaction
        conn = engine.connect()
        trans = conn.begin()
        try:
            for f in forecasts:
                sql = text('''
                INSERT INTO forecast_data (forecast_date, category, model_type, forecast_value, lower_bound, upper_bound, batch_num)
                VALUES (:forecast_date, :category, :model_type, :forecast_value, :lower_bound, :upper_bound, :batch_num)
                ON DUPLICATE KEY UPDATE
                  forecast_value = VALUES(forecast_value),
                  lower_bound = VALUES(lower_bound),
                  upper_bound = VALUES(upper_bound),
                  batch_num = VALUES(batch_num),
                  created_at = NOW()
                ''')
                conn.execute(sql, {
                    'forecast_date': f['forecast_date'],
                    'category': f['category'],
                    'model_type': f['model_type'],
                    'forecast_value': f['forecast_value'],
                    'lower_bound': f['lower_bound'],
                    'upper_bound': f['upper_bound'],
                    'batch_num': batch_num
                })
            trans.commit()
            print(f"Forecast saved for category: {cat}, {len(forecasts)} records")
        except Exception as e:
            trans.rollback()
            print('error writing forecasts for', cat, e)
        finally:
            conn.close()

if __name__ == '__main__':
    print('Forecast worker started, waiting for jobs...')
    while True:
        try:
            item = r.brpop('forecast_queue', timeout=5)
            if item:
                batch_num = item[1].decode('utf-8')
                print(f"Processing forecast job for batch: {batch_num}")
                process_batch(batch_num)
        except KeyboardInterrupt:
            print("Forecast worker shutting down...")
            break
        except Exception as e:
            print(f'Forecast worker error: {e}')
            import traceback
            traceback.print_exc()
            time.sleep(5)
