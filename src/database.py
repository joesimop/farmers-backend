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

# ENGINE FOR POSTGRES
engine = create_engine(database_connection_url(), pool_pre_ping=True)

# ENGINE FOR S3 BUCKET
# s3_resource = boto3.resource(
#     service_name='s3',
#     region_name='us-east-2',
#     aws_access_key_id= os.environ.get("AWS_ACCESS_KEY_ID"),
#     aws_secret_access_key= os.environ.get("AWS_SECRET_ACCESS_KEY")
# )

# s3_client = s3_resource.meta.client



# try:
#     object = s3_resource.Bucket("rareconnect").Object("WDA/images/confetti-1.png")

#     print(object.get()['Body'].read())

# except ClientError as e:
#     print(e)

