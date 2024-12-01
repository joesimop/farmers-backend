from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import  ForeignKeyViolation, UniqueViolation
from typing import Optional
from src.database_enum_types import TokenTransactorType
from decimal import Decimal
from src.global_models import MarketVendorFee
from src.api.vendor import Vendor
from src.helpers import before_equal_to_today
from src.CTE import market_tokens_cte, market_fees_cte, market_vendors_cte
from src.api.market_manager import get_market_date_options
from src.api_error_handling import handle_error, DatabaseError as db_error
from src.models import vendor_checkouts, token_deltas, vendor_checkout_tokens

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/market_manager/{market_manager_id}/checkout",
    tags=["checkout"],
)

class CheckoutOption(BaseModel):
    market_id: int
    market_name: str
    market_dates: list[datetime.date]

class CheckoutInit(BaseModel):
    vendors: list[Vendor]
    market_fees: list[MarketVendorFee]

class PaidToken(BaseModel):
    market_token_id: int
    count: int

class CheckoutSubmit(BaseModel):
    market_vendor_id: int
    market_date: datetime.date
    reported_gross: Decimal
    fees_paid: Decimal
    tokens: Optional[list[PaidToken]] = None


@router.get("/market_date_options")
def get_checkout_options(market_manager_id: int):
    """
    Gets the checkout options for a market manager.
    
    Returns:
    - JSONResponse: A list of checkout options.

    Raises:
    - HTTPException: If the market manager or markets are not found, a 404 error is raised.
    """
    return_list = get_market_date_options(market_manager_id)
    
    return JSONResponse(status_code=200, content=return_list)

@router.get("/market_details/{market_id}")
def init_checkout(market_manager_id: int, market_id: int, market_date: datetime.date = datetime.date.today()):
    """
    Initializes the checkout process.

    Parameters:
    - market_id (int): The id of the market.

    Returns:
    - JSONResponse: A list of vendors and market fees.

    Raises:
    - HTTPException: If the market is not found, a 404 error is raised.
    """
    
    #If the entered date is in the future, raise a 400 error
    if not before_equal_to_today(market_date):
        raise HTTPException(status_code=400, detail="Market date must be before or equal to today")

    try:
        with db.engine.begin() as conn:
            result = conn.execute(
                sqlalchemy.text(
                    f"WITH {market_vendors_cte}, {market_fees_cte}, {market_tokens_cte}," +
                    """
                    vendors_agg AS (
                        SELECT json_agg(market_vendors_cte) AS vendors
                        FROM market_vendors_cte 
                    ),

                    fees_agg AS (
                        SELECT COALESCE(json_agg(market_fees_cte), '[]'::json) AS market_fees
                        FROM market_fees_cte
                    ),
                    
                    tokens_agg AS (
                        SELECT COALESCE(json_agg(market_tokens_cte), '[]'::json) AS market_tokens
                        FROM market_tokens_cte
)

                    SELECT json_build_object('vendors', vendors_agg.vendors, 
                                            'market_fees', fees_agg.market_fees, 
                                            'market_tokens', tokens_agg.market_tokens) as body
                    FROM vendors_agg, fees_agg, tokens_agg
                    """
                ), {"market_id": market_id}
            ).fetchall()

    except DBAPIError as e:

        handle_error(e, db_error.FOREIGN_KEY_VIOLATION)
        
        raise HTTPException(status_code=500, detail="Database error")
    print(result[0][0])
    return JSONResponse(status_code=200, content=result[0][0])

@router.post("/submit")
def submit_checkout(checkout_submit: CheckoutSubmit):
    """
    Submits a checkout. Which involves the following steps:
    1.) Insert a new vendor_checkout record
    2.) Insert the tokens used as deltas
    3.) Insert the relations between the vendor_checkout and the tokens

    If any of these steps fail, the change will be rolled back.

    Parameters:
    - checkout_submit (CheckoutSubmit): The checkout submission.

    """

    try:
        with db.engine.begin() as conn:
            result = conn.execute(
                vendor_checkouts.insert().values(
                    market_vendor=checkout_submit.market_vendor_id,
                    market_date=checkout_submit.market_date,
                    gross=checkout_submit.reported_gross,
                    fees_paid=checkout_submit.fees_paid
                ).returning(vendor_checkouts.c.id)
            ).fetchall()

            #If the insert failed, raise a 500 error
            if result[0] is None:
                raise HTTPException(status_code=500, detail="Error inserting vendor checkout")
            
            vendor_checkout_id = result[0][0]

            #Insert the tokens used as deltas
            if checkout_submit.tokens is not None:
                token_delta_ids = conn.execute(
                    token_deltas.insert().returning(token_deltas.c.id), 
                    [
                        {
                            "market_token": token.market_token_id, 
                            "transactor": TokenTransactorType.Vendor.value,
                            "count":  token.count
                        } 
                        for token in checkout_submit.tokens
                    ]
                ).fetchall()

                
                #If the insert failed, raise a 500 error
                if token_delta_ids is []:
                    raise HTTPException(status_code=500, detail="Error inserting token deltas")
                
                #Insert the relations between the vendor_checkout and the tokens
                conn.execute(
                    vendor_checkout_tokens.insert(),
                    [
                        {
                            "vendor_checkout": vendor_checkout_id,
                            "token_delta": token_delta[0]
                        }
                        for token_delta in token_delta_ids
                    ]
                )
        

    except DBAPIError as e:

        handle_error(e, db_error.FOREIGN_KEY_VIOLATION, 
                        db_error.UNIQUE_VIOLATION,
                        db_error.NOT_NULL_VIOLATION)

        raise HTTPException(status_code=500, detail="Database error")
        
        
    return JSONResponse(status_code=200, content={"message": "Checkout submitted successfully"})

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
        
        error = handle_error(e, db_error.FOREIGN_KEY_VIOLATION)

        if error is not None:
            raise error

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