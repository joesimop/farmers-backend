from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation, NotNullViolation, ForeignKeyViolation
from typing import Optional
from src.database_enum_types import DaysOfWeek
from decimal import Decimal
from src.global_models import MarketVendorFee
from src.api.vendor import Vendor
from src.api.market import get_market_vendors
from src.helpers import before_equal_to_today

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


@router.post("")
def get_checkout_options(market_manager_id: int):
    """
    Gets the checkout options for a market manager.
    
    Returns:
    - JSONResponse: A list of checkout options.

    Raises:
    - HTTPException: If the market manager or markets are not found, a 404 error is raised.
    """

    try:
        with db.engine.begin() as conn:

            #First get manager's markets and their days of operation
            markets = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT markets.id, markets.name, string_agg(mf.day_of_week::TEXT, ',') as days
                    FROM markets
                    LEFT JOIN market_frequencies AS mf ON markets.id = mf.market_id
                    WHERE markets.manager_id = :manager_id
                    GROUP BY markets.id, markets.name
                    ORDER BY markets.name ASC
                    """
                ), {"manager_id": market_manager_id}
            ).fetchall()

            #If there is no markets, raise a 404
            if len(markets) == 0:
                raise HTTPException(status_code=404, detail="Market manager not found or manager has no markets")

            market_ids = tuple(market[0] for market in markets)

            #Get the 10 most recent market dates for each market, associate with market_id
            market_dates = conn.execute(
                sqlalchemy.text(
                    f"""
                    SELECT market_id, market_date
                    FROM 
                        (SELECT DISTINCT vm.market_id as market_id, market_date,
                            DENSE_RANK() OVER (PARTITION BY vm.market_id ORDER BY checkouts.market_date ASC) as rank
                        FROM vendor_checkouts as checkouts
                        JOIN market_vendors AS vm ON checkouts.market_vendor = vm.id
                        WHERE vm.market_id in :market_ids) as date_ranks
                    WHERE rank <= 10
                    ORDER BY market_date DESC
                    """
                ),{"market_ids": market_ids}
            ).fetchall()
    
    except DBAPIError as e:
        print(e)
        raise HTTPException(status_code=500, detail="Database error")
    
    #Populates the json response, kinda efficiently
    market_map = {}

    #Caching today's date and day of week
    today_date = datetime.date.today()
    today_string = today_date.isoformat()
    today_dow = DaysOfWeek.from_number(today_date.weekday())


    #For each market, we are gonna store a json object
    for market in markets:
        market_map[market[0]] = {
            "market_id": market[0],
            "market_name": market[1],
            "market_dates": []
        }

        #If today is a market day, we need to add it to the list because it
        #it may not be in the top 10 most recent dates
        if market[2] is not None:                                                   #Case where the market has no days of operation
            market_days = market[2].split(",")
            if today_dow.value in market_days:
                market_map[market[0]]["market_dates"].append(today_string)

    #Append all dates recorded in the database
    for date in market_dates:
        if date[1] != today_date:                                                    #Don't add today's date again
            market_map[date[0]]["market_dates"].append(date[1].isoformat())

    #Convert the map to a list
    return_list = [market_body for market_body in market_map.values()]

    return JSONResponse(status_code=200, content=return_list)

@router.post("/{market_id}")
def init_checkout(market_id: int, market_date: datetime.date = datetime.date.today()):
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