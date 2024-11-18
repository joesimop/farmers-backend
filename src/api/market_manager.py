from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation
from src.database_enum_types import DaysOfWeek
from src.api_error_handling import handle_error, DatabaseError as db_error

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

@router.get("/{market_manager_id}/markets")
def get_market_manager_markets(market_manager_id: int):
    """
    Gets all markets managed for a market manager.

    Parameters:
    """

    try:
        with db.engine.begin() as conn:
            markets = conn.execute(
                sqlalchemy.text(
                    f"""
                    SELECT id, name, city, state, created_at
                    FROM markets
                    WHERE manager_id = :manager_id
                    """
                ), {"manager_id": market_manager_id}
            ).fetchall()

    except DBAPIError as error:
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return_list = []

    for market in markets:
        return_list.append(
            {
                "id": market[0],
                "name": market[1],
                "city": market[2],
                "state": market[3],
                "created_at": market[4].isoformat()
            }
        )
    
    return JSONResponse(status_code=200, content=return_list)

@router.get("/{market_manager_id}/vendors_per_market")
def get_market_vendors(market_manager_id: int):
    """
    Gets all vendors for each market managed by a market manager.

    Parameters:
    - market_manager_id (int): The ID of the market manager.

    Returns:
    - JSONResponse: A list of markets and their associated vendors.

    Raises:
    - HTTPException: If there is an error during database interaction, it is caught, and an appropriate error message is printed.
    """
    try:
        with db.engine.begin() as conn:
            vendors_per_market = conn.execute(
                sqlalchemy.text(
                    f"""
                    SELECT 
                        json_build_object(
                            'market', m.name,
                            'vendors', json_agg(
                                json_build_object(
                                    'id', v.id,
                                    'business_name', v.business_name,
                                    'type', v.type,
                                    'current_cpc', v.current_cpc,
                                    'cpc_expr', v.cpc_expr
                                )
                            )
                        ) as market_vendors
                    FROM vendors AS v
                    JOIN market_vendors mv ON v.id = mv.vendor_id
                    JOIN markets m ON mv.market_id = m.id
                    WHERE m.manager_id = :manager_id
                    GROUP BY m.id
                    """
                ), {"manager_id": market_manager_id}
            ).fetchall()

    except DBAPIError as error:

        print(error)
        handle_error(error, db_error.FOREIGN_KEY_VIOLATION)

        raise(HTTPException(status_code=500, detail="Database error"))
    
    return JSONResponse(status_code=200, content=[vendors[0] for vendors in vendors_per_market])


def get_market_options(market_manager_id: int):
    """
    Gets the market options for a market manager.
    
    Returns:
    - JSONResponse: A list of checkout options.

    Raises:
    - HTTPException: If the market manager or markets are not found, a 404 error is raised.
    """

    try:
        with db.engine.begin() as conn:

            #First get manager's markets, their days of operation, and tokens
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
        
        handle_error(e, db_error.FOREIGN_KEY_VIOLATION)

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
    return [market_body for market_body in market_map.values()]