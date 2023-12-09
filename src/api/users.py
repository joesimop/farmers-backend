from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation

import sqlalchemy
from pydantic import BaseModel
from src import database as db
from src.schemas import user_credentials
from src import hashing
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/user",
    tags=["user"],
)

class UserCredentials(BaseModel):
    username: str
    password: str
    
class UserStorage(BaseModel):
    username: str
    salt: bytes
    pw_hash: bytes


@router.get("/")
def get_users():
    
    with db.engine.connect() as conn:

        result = conn.execute(
            sqlalchemy.select(user_credentials.c.username)
        )

        usernames = [row[0] for row in result.fetchall()]

        return usernames
    
@router.get("/tripscompleted")
def get_users():
    
    with db.engine.connect() as conn:

        result = conn.execute(
            sqlalchemy.text(
                "SELECT driver_id, COUNT(*) as Trips_Completed \
                FROM uber \
                WHERE status = 'Trip Completed' \
                GROUP BY driver_id \
                ORDER BY Trips_Completed DESC"
            )
        )

        tripscompleted = [{ "driverId": row[0], "tripsCompleted": row[1] }
                           for row in result.fetchall()]

        response = JSONResponse(content=tripscompleted, status_code=200)

        print(response.body)

        return response
    
@router.post("/create")
def create_user(user: UserCredentials):

    # Hash the password and store the salt and hash in the database
    salt, pw_hash = hashing.hash_new_password(user.password)

    try:

        with db.engine.begin() as conn:
            conn.execute(
                sqlalchemy
                .insert(user_credentials)
                .values(username=user.username, salt=salt, pw_hash=pw_hash)
            )

    except DBAPIError as error:

        if isinstance(error.orig, UniqueViolation):

            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        print("Error: ", error)
        
    return 201