from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation, NotNullViolation
from typing import Optional

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from src import hashing
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


@router.post("/create")
def create_market(market: Create_Market):
    """
    Creates a new market.

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
    except DBAPIError as e:
        
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=400, detail="Market already exists")
        
        if isinstance(e.orig, NotNullViolation):
            raise HTTPException(status_code=400, detail="Manager ID and Market Name are required")

        raise HTTPException(status_code=500, detail="Database error")

    return JSONResponse(content={"message": "Market created successfully"}, status_code=201)


@router.get("/{market_id}/vendors")
def get_market_vendors(market_id: int):
    """
    Get all vendors in a market.

    Parameters:
    - market_id (int): The id of the market to get vendors from.

    Returns:
    - JSONResponse: A JSON object containing the vendors in the market.

    Raises:
    - HTTPException: If there is an error during database interaction, it is caught, and an appropriate error message is printed.
    """

    try:
        with db.engine.begin() as conn:
            vendors = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT vendors.id, business_name, current_cpc, cpc_expr, vendors.type
                    FROM vendors
                    INNER JOIN vendors_at_markets ON vendors.id = vendors_at_markets.vendor_id
                    WHERE vendors_at_markets.market_id = :market_id
                    """
                ),
                {"market_id": market_id}
            ).fetchall()

    except DBAPIError as e:
        print(e)
        raise HTTPException(status_code=500, detail="Database error")

    return_list = []
    for vendor in vendors:
        return_list.append(
            {
                "id": vendor[0],
                "business_name": vendor[1],
                "current_cpc": vendor[2],
                "cpc_expr": vendor[3],
                "type": vendor[4]
            }
        )

    return JSONResponse(status_code=200, content=return_list)
