from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation
from typing import Optional
from src.database_enum_types import VendorType, FeeType, DaysOfWeek
from decimal import Decimal
from src.api_error_handling import handle_error, DatabaseError as db_error

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/market",
    tags=["market"],
)

class Market(BaseModel):
    id: int
    manager_id: int
    name: str
    city: str
    state: str
    created_at: datetime.datetime

class Create_Market(BaseModel):
    manager_id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    days_of_week: list[DaysOfWeek]

class Create_FeeForVendorType(BaseModel):
    market_id: int
    vendor_type: VendorType
    fee_type: FeeType
    rate: Decimal
    rate_2: Optional[Decimal] = None


@router.post("/create")
def create_market(market: Create_Market):
    """
    Creates a new market. The following steps are taken:
    1.) Insert the market into the database.
        - Market must have a manager_id and name.
        - City and State are optional.
    2.) Create the market days for the market.
        - Cannot register same day twice for the same market.

    Parameters:
    - market (Market): The market object containing: 
        manager_id, name, city, and state.

    Returns:
    - int: HTTP status code 201 indicating successful creation.

    Raises:
    - DBAPIError: If there is an error during database interaction, it is caught, and an appropriate error message is printed.

    Implementation Details:
    - Will return a message if no city or state is provided.
    """

    try:
        with db.engine.begin() as conn:

            #Insert market into database
            conn.execute(
                sqlalchemy.text(
            
                    """
                    INSERT INTO markets (manager_id, name, city, state)
                    VALUES (:manager_id, :name, :city, :state)
                    """
                    ),
                    {
                        "manager_id": market.manager_id,
                        "name": market.name,
                        "city": market.city,
                        "state": market.state
                    }
            )

            #Insert a relation for each market day
            #This is okay because it will be run a maximum of 7 times, and most likely 2 at most
            #Won't let duplicate days of week be for the same market
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO market_days (market_id, day_of_week)
                    VALUES (:market_id, :day_of_week)
                    """
                ),
                [
                    {
                        "market_id": market.id, 
                        "day_of_week": day.value
                    }
                    for day in market.days_of_week
                ]
            )


    # Note that technically, days of week execeptions are not being handled here.
    # Would have to split up the into different transaction
    except DBAPIError as e:

        handle_error(e, db_error.FOREIGN_KEY_VIOLATION,
                        db_error.NOT_NULL_VIOLATION,
                        db_error.UNIQUE_VIOLATION,
                        db_error.CHECK_VIOLATION)

        raise HTTPException(status_code=500, detail="Database error")


    return JSONResponse(status_code=201, content={"message": "Market created successfully"})


@router.get("/{market_id}/vendors")
def get_market_vendors_endpoint(market_id: int):
    """
    Get all vendors in a market.

    Parameters:
    - market_id (int): The id of the market to get vendors from.

    Returns:
    - JSONResponse: A JSON object containing the vendors in the market.

    Raises:
    - HTTPException: If there is an error during database interaction, it is caught, and an appropriate error message is printed.
    """

    return_list = get_market_vendors(market_id)

    return JSONResponse(status_code=200, content=return_list)

def get_market_vendors(market_id: int):
    """
    Parent Endpoint function as func def.
    Get all vendors in a market.
    """
    try:
        with db.engine.begin() as conn:
            vendors = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT vendors.id, business_name, current_cpc, cpc_expr, vendors.type
                    FROM vendors
                    JOIN market_vendors AS mv ON vendors.id = mv.vendor_id
                    WHERE mv.market_id = :market_id
                    """
                ),
                {"market_id": market_id}
            ).fetchall()

    except DBAPIError as e:
        raise HTTPException(status_code=500, detail="Database error")

    return_list = []
    for vendor in vendors:

        cpc_expr = vendor[3] if vendor[3] is None else vendor[3].isoformat()

        return_list.append(
            {
                "id": vendor[0],
                "business_name": vendor[1],
                "current_cpc": vendor[2],
                "cpc_expr": cpc_expr,
                "type": vendor[4]
            }
        )
    return return_list

@router.post("/create_fee_for_vendor_type")
def create_fee_for_vendor_type(body: Create_FeeForVendorType):
    """
    Create a fee for a vendor type in a market.

    Parameters:
    - market_id (int): The id of the market.
    - fee_type (FeeType): The type of fee to create.

    Returns:
    - JSONResponse: 201 status code indicating successful creation with message.

    Raises:
    - HTTPException: If the vendor type or fee type is invalid, 422 Invalid Data
    - HTTPException: Requires market id, vendor type, fee type, and at least one rate as input, 422 Bad Request
    - HTTPException: If a fee for this vendor type in this market already exists, 400 Bad Request 
    - HTTPException: If the market does not exist, 401 Not Found
    """

    try:
        with db.engine.begin() as conn:
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO market_fees (market_id, vendor_type, fee_type, rate, rate_2)
                    VALUES (:market_id, :vendor_type, :fee_type, :rate, :rate_2)
                    """
                ),
                {"market_id": body.market_id, 
                 "vendor_type": body.vendor_type.value,
                 "fee_type": body.fee_type.value,
                 "rate": body.rate,
                 "rate_2": body.rate_2}
            )

    except DBAPIError as e:

        handle_error(e, db_error.FOREIGN_KEY_VIOLATION,
                        db_error.NOT_NULL_VIOLATION,
                        db_error.CHECK_VIOLATION)
        
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=400, detail="A fee for this vendor type in this market already exists")
        
        raise HTTPException(status_code=500, detail="Database error")

    return JSONResponse(status_code=201, content={"message": "Fee created successfully"})

