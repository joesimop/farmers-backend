import sqlalchemy
from src import database as db

metadata = sqlalchemy.MetaData()
user_credentials = sqlalchemy.Table("user_credentials", metadata, autoload_with=db.engine)