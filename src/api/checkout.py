from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation, NotNullViolation, ForeignKeyViolation
from typing import Optional
from src.database_enum_types import VendorType, FeeType
from decimal import Decimal
from src.global_models import MarketVendorFee
from src.api.vendor import Vendor
from src.api.market import get_market_vendors

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/market/{market_id}/checkout",
    tags=["checkout"],
)

class CheckoutInit(BaseModel):
    vendors: list[Vendor]
    market_fees: list[MarketVendorFee]


@router.post("/init")
def init_checkout(market_id: int):
    """
    Initializes the checkout process.

    Parameters:
    - market_id (int): The id of the market.

    Returns:
    - JSONResponse: A list of vendors and market fees.

    Raises:
    - HTTPException: If the market is not found, a 404 error is raised.
    """
    
    vendors = get_market_vendors(market_id)
    market_fees = get_market_fees(market_id)

    return_val = {
        "vendors": vendors,
        "market_fees": market_fees
    }

    return JSONResponse(status_code=200, content=return_val)

@router.get("/market_fees")
def get_market_fees_endpoint(market_id: int):
    """
    Wrapper endpoint for get_market_fees.
    """
    
    return_list = get_market_fees(market_id)
    
    return JSONResponse(status_code=200, content=return_list)


def get_market_fees(market_id: int):
    """
    Gets the fees associated with a market.

    Parameters:
    - market_id (int): The id of the market.

    Returns:
    - Python JSON List: A list of market fees.

    Raises:
    - HTTPException: If the market is not found, a 404 error is raised.
    """

    try:
        with db.engine.begin() as conn:
            result = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT * FROM market_fees
                    WHERE market_id = :market_id
                    """
                ),
                {"market_id": market_id}
            )

    except DBAPIError as e:
        
        if isinstance(e.orig, ForeignKeyViolation):
            raise HTTPException(status_code=404, detail="Market not found")

        raise HTTPException(status_code=500, detail="Database error")
    
    return_list = []

    for row in result:
        return_list.append(
            MarketVendorFee(
                vendor_type=row[1],
                fee_type=row[2],
                rate=row[3],
                rate_2=row[4]
            ).toJSON()
        )
    return return_list