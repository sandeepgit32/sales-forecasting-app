import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import hashlib
import time
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from common.db import SessionLocal, engine
from common.models import UploadMetadata, InvoiceData, ForecastData

UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/app/data/uploaded_files')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
DB = SessionLocal()

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_DIR'] = UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

import redis
r = redis.from_url(REDIS_URL)

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'only csv allowed'}), 400

    original_filename = secure_filename(file.filename)
    # read to memory to compute hash
    content = file.read()
    sha = hashlib.sha256(content).hexdigest()

    existing = DB.query(UploadMetadata).filter(UploadMetadata.file_hash == sha).first()
    if existing:
        return jsonify({'error': 'duplicate file', 'batch_num': existing.batch_num}), 409

    ts = int(time.time())
    stored_filename = f"{os.path.splitext(original_filename)[0]}_{ts}_{sha[:8]}.csv"
    stored_path = os.path.join(app.config['UPLOAD_DIR'], stored_filename)

    # write file
    with open(stored_path, 'wb') as f:
        f.write(content)

    batch_num = f"{os.path.splitext(original_filename)[0]}_{ts}_{uuid.uuid4().hex[:6]}"

    metadata = UploadMetadata(
        batch_num=batch_num,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_hash=sha,
        status='uploaded'
    )
    try:
        DB.add(metadata)
        DB.commit()
    except IntegrityError as e:
        DB.rollback()
        return jsonify({'error': 'db error', 'detail': str(e)}), 500

    # push ETL job to redis list
    job_payload = {'batch_num': batch_num, 'stored_filename': stored_filename}
    r.lpush('etl_queue', str(job_payload))

    return jsonify({'message': 'file accepted', 'batch_num': batch_num}), 201

@app.route('/metadata', methods=['GET'])
def metadata_list():
    items = DB.query(UploadMetadata).order_by(UploadMetadata.uploaded_at.desc()).limit(100).all()
    result = []
    for m in items:
        result.append({
            'batch_num': m.batch_num,
            'original_filename': m.original_filename,
            'stored_filename': m.stored_filename,
            'file_hash': m.file_hash,
            'uploaded_at': m.uploaded_at.isoformat() if m.uploaded_at else None,
            'num_total_rows': m.num_total_rows,
            'num_missing_rows': m.num_missing_rows,
            'num_imputed_rows': m.num_imputed_rows,
            'num_inserted_rows': m.num_inserted_rows,
            'num_updated_rows': m.num_updated_rows,
            'status': m.status,
            'error_log': m.error_log
        })
    return jsonify(result)

@app.route('/invoice-data', methods=['GET'])
def invoice_data_list():
    """Get invoice data with optional filtering by category and date range"""
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 1000))
    
    query = DB.query(InvoiceData)
    
    if category:
        query = query.filter(InvoiceData.category == category)
    if start_date:
        query = query.filter(InvoiceData.date >= start_date)
    if end_date:
        query = query.filter(InvoiceData.date <= end_date)
    
    items = query.order_by(InvoiceData.date.desc()).limit(limit).all()
    result = []
    for item in items:
        result.append({
            'date': item.date.isoformat() if item.date else None,
            'product_id': item.product_id,
            'category': item.category,
            'sales': float(item.sales),
            'is_imputed': item.is_imputed,
            'batch_num': item.batch_num,
            'version': item.version
        })
    return jsonify(result)

@app.route('/forecast-data', methods=['GET'])
def forecast_data_list():
    """Get forecast data with optional filtering by category and model type"""
    category = request.args.get('category')
    model_type = request.args.get('model_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 1000))
    
    query = DB.query(ForecastData)
    
    if category:
        query = query.filter(ForecastData.category == category)
    if model_type:
        query = query.filter(ForecastData.model_type == model_type)
    if start_date:
        query = query.filter(ForecastData.forecast_date >= start_date)
    if end_date:
        query = query.filter(ForecastData.forecast_date <= end_date)
    
    items = query.order_by(ForecastData.forecast_date.desc()).limit(limit).all()
    result = []
    for item in items:
        result.append({
            'id': item.id,
            'forecast_date': item.forecast_date.isoformat() if item.forecast_date else None,
            'category': item.category,
            'model_type': item.model_type,
            'forecast_value': float(item.forecast_value),
            'lower_bound': float(item.lower_bound) if item.lower_bound else None,
            'upper_bound': float(item.upper_bound) if item.upper_bound else None,
            'batch_num': item.batch_num
        })
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
