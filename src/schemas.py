import sqlalchemy
from src import database as db

metadata = sqlalchemy.MetaData()
user_credentials = sqlalchemy.Table("user_credentials", metadata, autoload_with=db.engine)
user_profiles = sqlalchemy.Table("user_profiles", metadata, autoload_with=db.engine)
communities = sqlalchemy.Table("communities", metadata, autoload_with=db.engine)
community_applications = sqlalchemy.Table("community_applications", metadata, autoload_with=db.engine)
roles = sqlalchemy.Table("roles", metadata, autoload_with=db.engine)
community_requests = sqlalchemy.Table("community_requests", metadata, autoload_with=db.engine)
