from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import  ForeignKeyViolation
from src.api.market_manager import get_market_date_options
from src.order_by import user_sortable_endpoint, SortOption, SortDirection

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

    return_list = get_market_date_options(market_manager_id, False)
    return_list.insert(0, {"market_id": 0, "market_name": "All Markets", "market_dates": []})

    return JSONResponse(status_code=200, content=return_list)

@router.get("/report")
@user_sortable_endpoint(SortOption.MarketDate, SortOption.VendorName, SortOption.Gross, SortOption.FeesPaid)
def get_report(market_manager_id: int,
               market_id: int, 
               market_date: datetime.date | None = None, 
               sort_by: SortOption | None = SortOption.MarketDate, 
               sort_direction: SortDirection | None = SortDirection.Descending):
    """
    """

    #If market_id or date is None, then use all valid entries
    where_clause = ""
    if market_id != 0:
        where_clause += " AND mv.market_id = :market_id"
    if market_date is not None:
        where_clause += " AND market_date = :market_date"
        market_date = market_date.isoformat()

    try:
        with db.engine.begin() as conn:
            reports = conn.execute(
                sqlalchemy.text(
                    f"""
                    WITH market_token_deltas AS (
                        SELECT 
                            vc.id AS vendor_checkout_id,
                            mt.id AS token_id,
                            mt.token_type,
                            mt.per_dollar_value,
                            COALESCE(SUM(td.delta), 0) AS token_delta
                        FROM vendor_checkouts vc
                        JOIN market_vendors mv ON vc.market_vendor = mv.id
                        JOIN market_tokens mt ON mt.market_id = mv.market_id
                        LEFT JOIN vendor_checkout_tokens vct ON vct.vendor_checkout = vc.id
                        LEFT JOIN token_deltas td ON vct.token_delta = td.id AND td.market_token = mt.id
                        GROUP BY vc.id, mt.id, mt.token_type, mt.per_dollar_value
                    )

                    SELECT 
                        json_build_object(
                            'id', vc.id,
                            'business_name', v.business_name, 
                            'vendor_type', v.type,
                            'gross', vc.gross, 
                            'fees_paid', vc.fees_paid,
                            'market_date', vc.market_date,
                            'tokens', json_agg(
                                json_build_object(
                                    'type', mtd.token_type, 
                                    'count', mtd.token_delta,
                                    'per_dollar_value', mtd.per_dollar_value
                                ) ORDER BY mtd.token_id
                            )
                        ) AS checkouts
                    FROM vendor_checkouts AS vc
                    JOIN market_vendors AS mv ON vc.market_vendor = mv.id
                    JOIN vendors AS v ON mv.vendor_id = v.id
                    JOIN markets AS m ON mv.market_id = m.id
                    JOIN market_token_deltas mtd ON mtd.vendor_checkout_id = vc.id
                    WHERE m.manager_id = :market_manager_id {where_clause}
                    GROUP BY vc.id, v.business_name, v.type, vc.gross, vc.fees_paid, vc.market_date
                    ORDER BY {sort_by} {sort_direction}
                   """
                ), {"market_manager_id": market_manager_id,
                    "market_id": market_id, 
                    "market_date": market_date
                }
            ).fetchall()
            
    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    

    return JSONResponse(status_code=200, content=[report[0] for report in reports])