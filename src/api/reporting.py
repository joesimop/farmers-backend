from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import  ForeignKeyViolation
from typing import Optional
from src.database_enum_types import DaysOfWeek, TokenTransactorType
from decimal import Decimal
from src.global_models import MarketVendorFee
from src.api.vendor import Vendor
from src.helpers import before_equal_to_today
from src.CTE import market_tokens_cte, market_fees_cte, market_vendors_cte
from src.api.market_manager import get_market_options

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/market_manager/{market_manager_id}/reporting",
    tags=["reporting"],
)

@router.get("/options")
def get_report_options(market_manager_id: int):
    """
    Gets the report options for a market manager.
    Exact same as get_checkout_options, but adds a market called "All Vendors" with market_id 0.
    """

    return_list = get_market_options(market_manager_id)
    return_list.insert(0, {"market_id": 0, "market_name": "All Markets", "market_dates": []})

    return JSONResponse(status_code=200, content=return_list)


    