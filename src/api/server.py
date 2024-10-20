from fastapi import FastAPI, exceptions
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from src.api import profile, people, market_manager, checkout, vendor, market
import json
import logging
from starlette.middleware.cors import CORSMiddleware
import sys

description = """
Backend for Main Street Market.
"""

app = FastAPI(
    title="Main Street Market Backend",
    description=description,
    version="0.0.1",
    terms_of_service="",
    contact={
        "name": "Joe and Zach Simopoulos",
        "email": "joesimop8@gmail.com",
    },
)

app.include_router(market_manager.router)
app.include_router(vendor.router)
app.include_router(checkout.router)
app.include_router(market.router)

@app.exception_handler(exceptions.RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"The client sent invalid data!: {exc}")
    exc_json = exc.errors()

    #Check for sorting input error
    if exc_json[0]["loc"][1] == "sort_by":
        response = {"detail": "Invalid sort_by value"}
        return JSONResponse(response, status_code=422)
    
    elif exc_json[0]["loc"][1] == "sort_direction":
        response = {"detail": "Invalid sort_direction value"}
        return JSONResponse(response, status_code=422)
    
    else:

        response = {"detail": []}

        if len(exc_json) == 1:
            response['detail'] = f"{exc_json[0]['loc']}: {exc_json[0]['msg']}"
        else:
            for error in exc_json:
                response['detail'].append(f"{error['loc']}: {error['msg']}")

        return JSONResponse(response, status_code=422)

@app.get("/")
async def root():
    return {"message": "Backend Application for Farmer's Market"}
