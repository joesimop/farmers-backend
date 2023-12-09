import os
import dotenv
from sqlalchemy import create_engine

def database_connection_url():
    dotenv.load_dotenv()

    # FOR MYSQL
    # user = os.environ.get("DB_USER")
    # password = os.environ.get("DB_PASSWORD")
    # host = os.environ.get("HOSTNAME")
    # port = os.environ.get("PORT")
    # return f'mysql+pymysql://{user}:{password}@{host}:{port}/{user}?charset=utf8mb4'
    
    return os.environ.get("POSTGRES_URI")

engine = create_engine(database_connection_url(), pool_pre_ping=True)
