import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ''))
from common.db import engine
from common.models import Base

if __name__ == '__main__':
    print('Creating tables (if not exists) ...')
    Base.metadata.create_all(bind=engine)
    print('Done')
