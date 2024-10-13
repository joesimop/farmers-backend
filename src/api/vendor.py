from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation, ForeignKeyViolation
from src.database_enum_types import VendorType
from src.global_models import IdConcealer
from typing import Optional

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
            conn.execute(
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
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))

    # Notify the user if no cpc number or expiration was provided
    return_message = "Vendor created successfully."
    if vendor.current_cpc is None or vendor.cpc_expr is None:
        return_message = return_message + " No CPC number or expiration was provided."

    return JSONResponse(status_code=201, content={"message": return_message})

@router.post("/{vendor_id}/join_market")
def join_market(vendor_id: int, market: IdConcealer):
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
                    INSERT INTO vendors_at_markets (market_id, vendor_id)
                    VALUES (:market_id, :vendor_id)
                    """
                    ),

                    {
                        "market_id": market.id,
                        "vendor_id": vendor_id
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