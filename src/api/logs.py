from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_credentials, user_profiles, communities
from src import hashing
from sqlalchemy.exc import DBAPIError
from enum import Enum

router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)

class ProfileCommunity(BaseModel):
    profile_id: int
    community_id: int

class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class LogEvent(str, Enum):
    APP_CLOSE = "APP_CLOSE"


@router.post("/app_close")
def app_close(user: ProfileCommunity):
    """
    Log when the app is closed
    """
    try:
        with db.engine.begin() as conn:
            user = conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO logs.events (log_level, event, profile_id, community_id)
                    VALUES (:log_level, :event, :profile_id, :community_id)
                    """
                ), ({"profile_id": user.profile_id, "log_level": LogLevel.INFO.value, "event": LogEvent.APP_CLOSE.value, "community_id": user.community_id})
            )

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    