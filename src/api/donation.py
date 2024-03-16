from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation, UniqueViolation

import sqlalchemy
import datetime, decimal
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_profiles, community_requests
from sqlalchemy.exc import DBAPIError


router = APIRouter(
    prefix="/communities/{c_id}/donation",
    tags=["donation"],
)


class DonationLedger(BaseModel):
    profile_id: int
    amount: decimal.Decimal
    timestamp: datetime.datetime

@router.get("/page")
def get_page(c_id : int):

    try:
        with db.engine.begin() as conn:

            message = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT message
                    FROM donation_page
                    WHERE community_id = :community_id
                    """
                ), ({"community_id" : c_id})
            ).scalar_one_or_none()

    except DBAPIError as error:
            
            raise(HTTPException(status_code=500, detail="Database error"))
    
    if message is None:
        raise(HTTPException(status_code=404, detail="No message found for this community"))
    
    return JSONResponse(content={"message" : message}, status_code=200)

@router.post("/donate")
def make_donation(c_id : int, donation: DonationLedger):
     
    try: 
        with db.engine.begin() as conn:
            
            conn.execute(
                sqlalchemy.text(
                        """
                        INSERT INTO donation_ledger (community_id, profile_id, amount, timestamp)
                        VALUES (:community_id, :profile_id, :amount, :donation_date)
                        """
                ), ({"community_id" : c_id,
                    "profile_id" : donation.profile_id, 
                    "amount" : donation.amount,
                    "timestamp" : donation.timestamp})
            )

    except DBAPIError as error:
            
            raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201
