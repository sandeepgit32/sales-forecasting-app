import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import time
from datetime import timedelta
import redis
import pandas as pd
import numpy as np
from sqlalchemy import text
from common.db import engine, SessionLocal
from prophet import Prophet
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
warnings.filterwarnings('ignore')

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

def forecast_prophet(df, horizon):
    """Generate forecast using FB Prophet"""
    try:
        # Prepare data for Prophet
        prophet_df = df.reset_index().rename(columns={'date': 'ds', 'sales': 'y'})
        
        # Create and fit model
        model = Prophet(
            interval_width=0.95,
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True
        )
        model.fit(prophet_df)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=horizon, freq='D')
        
        # Make predictions
        forecast = model.predict(future)
        
        # Extract only future predictions
        forecast = forecast.tail(horizon)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(
            columns={'ds': 'date', 'yhat': 'forecast', 'yhat_lower': 'lower', 'yhat_upper': 'upper'}
        )
    except Exception as e:
        print(f"Prophet forecast error: {e}")
        return None

def forecast_sarimax(df, horizon):
    """Generate forecast using SARIMAX"""
    try:
        # Ensure we have enough data
        if len(df) < 14:
            return None
        
        # Fit SARIMAX model with simple parameters
        model = SARIMAX(
            df['sales'],
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        
        fitted_model = model.fit(disp=False, maxiter=100)
        
        # Generate forecast
        forecast_result = fitted_model.get_forecast(steps=horizon)
        forecast_mean = forecast_result.predicted_mean
        forecast_ci = forecast_result.conf_int(alpha=0.05)
        
        # Create result dataframe
        last_date = df.index.max()
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq='D')
        
        result = pd.DataFrame({
            'date': forecast_dates,
            'forecast': forecast_mean.values,
            'lower': forecast_ci.iloc[:, 0].values,
            'upper': forecast_ci.iloc[:, 1].values
        })
        
        return result
    except Exception as e:
        print(f"SARIMAX forecast error: {e}")
        return None

def forecast_holt_winters(df, horizon):
    """Generate forecast using Holt-Winters Exponential Smoothing"""
    try:
        # Ensure we have enough data
        if len(df) < 14:
            return None
        
        # Fit Holt-Winters model
        model = ExponentialSmoothing(
            df['sales'],
            seasonal_periods=7,
            trend='add',
            seasonal='add',
            initialization_method='estimated'
        )
        
        fitted_model = model.fit()
        
        # Generate forecast
        forecast_values = fitted_model.forecast(steps=horizon)
        
        # Calculate confidence intervals (approximate using standard error)
        residuals = fitted_model.fittedvalues - df['sales']
        std_error = np.std(residuals)
        
        # 95% confidence interval (approximately 1.96 * std error)
        margin = 1.96 * std_error
        
        # Create result dataframe
        last_date = df.index.max()
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq='D')
        
        result = pd.DataFrame({
            'date': forecast_dates,
            'forecast': forecast_values.values,
            'lower': (forecast_values - margin).values,
            'upper': (forecast_values + margin).values
        })
        
        return result
    except Exception as e:
        print(f"Holt-Winters forecast error: {e}")
        return None

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
        if df.empty or len(df) < 7:
            print(f"Skipping category {cat}: insufficient data (need at least 7 days)")
            continue
            
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        # Generate forecasts for each model
        forecasts = []
        
        # Prophet forecast
        prophet_result = forecast_prophet(df, HORIZON)
        if prophet_result is not None:
            for _, row in prophet_result.iterrows():
                forecasts.append({
                    'forecast_date': row['date'].date(),
                    'category': cat,
                    'model_type': 'prophet',
                    'forecast_value': round(float(row['forecast']), 2),
                    'lower_bound': round(float(row['lower']), 2),
                    'upper_bound': round(float(row['upper']), 2)
                })
        
        # SARIMAX forecast
        sarimax_result = forecast_sarimax(df, HORIZON)
        if sarimax_result is not None:
            for _, row in sarimax_result.iterrows():
                forecasts.append({
                    'forecast_date': row['date'].date(),
                    'category': cat,
                    'model_type': 'sarimax',
                    'forecast_value': round(float(row['forecast']), 2),
                    'lower_bound': round(float(row['lower']), 2),
                    'upper_bound': round(float(row['upper']), 2)
                })
        
        # Holt-Winters forecast
        hw_result = forecast_holt_winters(df, HORIZON)
        if hw_result is not None:
            for _, row in hw_result.iterrows():
                forecasts.append({
                    'forecast_date': row['date'].date(),
                    'category': cat,
                    'model_type': 'holt_winters',
                    'forecast_value': round(float(row['forecast']), 2),
                    'lower_bound': round(float(row['lower']), 2),
                    'upper_bound': round(float(row['upper']), 2)
                })

        if not forecasts:
            print(f"No forecasts generated for category {cat}")
            continue

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
