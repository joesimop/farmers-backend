from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from src import hashing
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/market_manager",
    tags=["market_manager"],
)

class MarketManager(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: str
    created_at: datetime.datetime

class Create_MarketManager(BaseModel):
    firstname: str
    lastname: str
    email: str

@router.post("/create")
def create_market_manager(market_manager: Create_MarketManager):
    """
    Creates a new market manager.

    Parameters:
    - market_manager (MarketManager): The market manager object containing: 
        firstname, lastname, and email.

    Returns:
    - int: HTTP status code 201 indicating successful creation.

    Raises:
    - DBAPIError: If there is an error during database interaction, it is caught, and an appropriate error message is printed.

    Implementation Details:
    - The function creates a new market manager with the provided information.
    """
    try:
        with db.engine.begin() as conn:
            conn.execute(
                sqlalchemy.text(
            
                    """
                    INSERT INTO market_managers (firstname, lastname, email)
                    VALUES (:firstname, :lastname, :email)
                    """
                    ),
                    {
                        "firstname": market_manager.firstname,
                        "lastname": market_manager.lastname,
                        "email": market_manager.email
                    }
                    
            )
    
    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return JSONResponse(status_code=201, content={"detail": "Market manager created successfully."})


