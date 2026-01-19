from sqlalchemy import Column, String, Integer, Date, DateTime, DECIMAL, Boolean, Enum, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class UploadMetadata(Base):
    __tablename__ = 'upload_metadata'
    batch_num = Column(String(100), primary_key=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, unique=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    num_total_rows = Column(Integer, default=0)
    num_missing_rows = Column(Integer, default=0)
    num_imputed_rows = Column(Integer, default=0)
    num_inserted_rows = Column(Integer, default=0)
    num_updated_rows = Column(Integer, default=0)
    status = Column(Enum('uploaded','processing','completed','failed'), default='uploaded')
    error_log = Column(Text)

class InvoiceData(Base):
    __tablename__ = 'invoice_data'
    date = Column(Date, primary_key=True)
    product_id = Column(String(100), primary_key=True)
    category = Column(String(100), primary_key=True)
    sales = Column(DECIMAL(12,2), nullable=False)
    is_imputed = Column(Boolean, default=False)
    batch_num = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    version = Column(Integer, default=1)

class ForecastData(Base):
    __tablename__ = 'forecast_data'
    id = Column(Integer, primary_key=True)
    forecast_date = Column(Date, nullable=False)
    category = Column(String(100), nullable=False)
    model_type = Column(Enum('prophet','sarimax','holt_winters'), nullable=False)
    forecast_value = Column(DECIMAL(12,2), nullable=False)
    lower_bound = Column(DECIMAL(12,2))
    upper_bound = Column(DECIMAL(12,2))
    created_at = Column(DateTime, server_default=func.now())
    batch_num = Column(String(100))
    __table_args__ = (UniqueConstraint('forecast_date', 'category', 'model_type', name='unique_forecast'),)
