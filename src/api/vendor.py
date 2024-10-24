from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation, ForeignKeyViolation
from src.database_enum_types import VendorType
from src.global_models import IdConcealer
from typing import Optional
from src.api_error_handling import handle_error, DatabaseError as db_error

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from src import hashing
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/vendor",
    tags=["vendor"],
)

class Vendor(BaseModel):
    id: int
    business_name: str
    current_cpc: str
    cpc_expr: datetime.datetime
    type: VendorType
    created_at: datetime.datetime

class Create_Vendor(BaseModel):
    business_name: str
    current_cpc: Optional[str] = None
    cpc_expr: Optional[datetime.datetime] = None
    type: VendorType

class VendorJoinMarket(BaseModel):
    vendor_id: int
    market_id: int


@router.post("/create")
def create_vendor(vendor: Create_Vendor):
    """
    Creates a new vendor.

    Parameters:
    - vendor (Vendor): The vendor object containing: 
        business_name, current_cpc, cpc_expr, and type.

    Returns:
    - int: HTTP status code 201 indicating successful creation.

    Raises:
    - DBAPIError: If there is an error during database interaction, it is caught, and an appropriate error message is printed.

    Implementation Details:
    - Will return a message if no cpc number or expiration is provided.
    """
    try:
        with db.engine.begin() as conn:
            vendor_id = conn.execute(
                sqlalchemy.text(
            
                    """
                    INSERT INTO vendors (business_name, current_cpc, cpc_expr, type)
                    VALUES (:business_name, :current_cpc, :cpc_expr, :type)
                    RETURNING id
                    """
                    ),

                    {
                        "business_name": vendor.business_name,
                        "current_cpc": vendor.current_cpc,
                        "cpc_expr": vendor.cpc_expr,
                        "type": vendor.type.value
                    }

            )

    except DBAPIError as error:
        
        handle_error(error, db_error.NOT_NULL_VIOLATION,
                            db_error.UNIQUE_VIOLATION)

        raise(HTTPException(status_code=500, detail="Database error"))

    #If we didn't get an id back, something went wrong
    if vendor_id.inserted_primary_key is None:
        raise(HTTPException(status_code=500, detail="Insert to database failed"))
    else:
        vendor_id = vendor_id.inserted_primary_key[0]
    
    # Notify the user if no cpc number or expiration was provided
    return_message = "Vendor created successfully."

    return JSONResponse(status_code=201, content={"id": vendor_id, "detail": return_message})

@router.post("/join_market")
def join_market(market_vendor: VendorJoinMarket):
    """
    Allows a vendor to join a market.

    Parameters:
    - vendor_id (int): The ID of the vendor.
    - market (IdConcealer): The ID of the market.

    Returns:
    - int: HTTP status code 201 indicating successful creation.

    Raises:
    - HTTPException: If the vendor has already joined the market, 400 Bad Request
    - HTTPException: If the market or vendor does not exist, 400 Bad Request
    - DBAPIError: If there is an error during database interaction, it is caught, and an appropriate error message is printed.
    """

    try:
        with db.engine.begin() as conn:
            conn.execute(
                sqlalchemy.text(
            
                    """
                    INSERT INTO market_vendors (market_id, vendor_id)
                    VALUES (:market_id, :vendor_id)
                    """
                    ),

                    {
                        "market_id": market_vendor.market_id,
                        "vendor_id": market_vendor.vendor_id
                    }

            )
    except DBAPIError as error:
        
        if isinstance(error.orig, UniqueViolation):
            raise HTTPException(
                status_code=400,
                detail="Vendor already joined this market"
            )
        
        if isinstance(error.orig, ForeignKeyViolation):
            raise HTTPException(
                status_code=400,
                detail="Market or vendor does not exist"
            )

        raise(HTTPException(status_code=500, detail="Database error"))

    return JSONResponse(status_code=201, content={"message": "Vendor joined market successfully."})