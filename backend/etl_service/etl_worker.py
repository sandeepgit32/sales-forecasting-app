import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import ast
import time
import pandas as pd
import redis
from sqlalchemy import text
from common.db import engine, SessionLocal
from common.models import UploadMetadata

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/app/data/uploaded_files')

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

def process_batch(batch_num, stored_filename):
    metadata = DB.query(UploadMetadata).filter(UploadMetadata.batch_num == batch_num).first()
    if not metadata:
        print(f"metadata not found for {batch_num}")
        return
    metadata.status = 'processing'
    DB.commit()

    path = os.path.join(UPLOAD_DIR, stored_filename)
    try:
        df = pd.read_csv(path, parse_dates=['Date'])
    except Exception as e:
        metadata.status = 'failed'
        metadata.error_log = str(e)
        DB.commit()
        return

    # Validate required columns
    required = {'Date', 'product_id', 'category', 'sales'}
    if not required.issubset(set(df.columns)):
        metadata.status = 'failed'
        metadata.error_log = f"missing columns: {required - set(df.columns)}"
        DB.commit()
        return

    metadata.num_total_rows = int(len(df))
    # Count missing rows in sales
    metadata.num_missing_rows = int(df['sales'].isna().sum())

    # Imputation: forward fill then fill with 0
    imputed_mask = df['sales'].isna()
    df['sales'] = df['sales'].ffill().fillna(0)
    df['is_imputed'] = imputed_mask
    metadata.num_imputed_rows = int(imputed_mask.sum())

    inserted = 0
    updated = 0

    conn = engine.connect()
    trans = conn.begin()
    try:
        for _, row in df.iterrows():
            date = row['Date'].date() if hasattr(row['Date'], 'date') else row['Date']
            product_id = str(row['product_id'])
            category = str(row['category'])
            sales = float(row['sales'])
            is_imputed = bool(row['is_imputed'])

            # Try insert, if fails do update
            try:
                sql = text("""
                INSERT INTO invoice_data (`date`, product_id, category, sales, is_imputed, batch_num, file_hash, version)
                VALUES (:date, :product_id, :category, :sales, :is_imputed, :batch_num, :file_hash, 1)
                """)
                conn.execute(sql, {
                    'date': date,
                    'product_id': product_id,
                    'category': category,
                    'sales': sales,
                    'is_imputed': is_imputed,
                    'batch_num': metadata.batch_num,
                    'file_hash': metadata.file_hash
                })
                inserted += 1
            except Exception:
                # Update existing record
                update_sql = text("""
                UPDATE invoice_data SET
                  sales = :sales,
                  is_imputed = :is_imputed,
                  batch_num = :batch_num,
                  file_hash = :file_hash,
                  version = version + 1,
                  updated_at = NOW()
                WHERE `date` = :date AND product_id = :product_id AND category = :category
                """)
                res = conn.execute(update_sql, {
                    'sales': sales,
                    'is_imputed': is_imputed,
                    'batch_num': metadata.batch_num,
                    'file_hash': metadata.file_hash,
                    'date': date,
                    'product_id': product_id,
                    'category': category
                })
                updated += res.rowcount if res is not None else 1

        trans.commit()
    except Exception as e:
        trans.rollback()
        metadata.status = 'failed'
        metadata.error_log = str(e)
        DB.commit()
        conn.close()
        return

    conn.close()
    metadata.num_inserted_rows = inserted
    metadata.num_updated_rows = updated
    metadata.status = 'completed'
    DB.commit()

    # push to forecast queue
    r.lpush('forecast_queue', batch_num)
    print(f"Processed {batch_num}: inserted={inserted} updated={updated}")


if __name__ == '__main__':
    print("ETL worker started, waiting for jobs...")
    while True:
        try:
            item = r.brpop('etl_queue', timeout=5)
            if item:
                # item is (queue_name, value)
                raw = item[1].decode('utf-8')
                try:
                    job = ast.literal_eval(raw)
                    batch_num = job.get('batch_num')
                    stored_filename = job.get('stored_filename')
                    print(f"Processing job: batch_num={batch_num}, file={stored_filename}")
                    process_batch(batch_num, stored_filename)
                except Exception as job_error:
                    print(f'Error processing job {raw}: {job_error}')
                    import traceback
                    traceback.print_exc()
        except KeyboardInterrupt:
            print("ETL worker shutting down...")
            break
        except Exception as e:
            print(f'ETL worker error: {e}')
            import traceback
            traceback.print_exc()
            time.sleep(5)
