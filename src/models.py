import sqlalchemy
from src import database as db

metadata = sqlalchemy.MetaData()
vendor_checkouts = sqlalchemy.Table("vendor_checkouts", metadata, autoload_with=db.engine)
token_deltas = sqlalchemy.Table("token_deltas", metadata, autoload_with=db.engine)
vendor_checkout_tokens = sqlalchemy.Table("vendor_checkout_tokens", metadata, autoload_with=db.engine)
vendors = sqlalchemy.Table("vendors", metadata, autoload_with=db.engine)
vendor_producer_contacts = sqlalchemy.Table("vendor_producer_contacts", metadata, autoload_with=db.engine)