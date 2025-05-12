import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Config:
    TOKEN = os.environ.get('TOKEN')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'data/app.db')
    ADMIN_ID = os.environ.get('ADMIN_ID')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))