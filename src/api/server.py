from fastapi import FastAPI, exceptions
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from src.api import profile, community, communityspecific, guidelines
import json
import logging
from starlette.middleware.cors import CORSMiddleware
import sys

description = """
Backend for RareConnect.
"""

app = FastAPI(
    title="RareConnectBakend",
    description=description,
    version="0.0.1",
    terms_of_service="",
    contact={
        "name": "Joseph Simopoulos",
        "email": "joesimop8@gmail.com",
    },
)

app.include_router(profile.router)
app.include_router(community.router)
app.include_router(communityspecific.router)
app.include_router(guidelines.router)
# app.include_router(carts.router)
# app.include_router(catalog.router)
# app.include_router(bottler.router)
# app.include_router(barrels.router)
# app.include_router(admin.router)

@app.exception_handler(exceptions.RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"The client sent invalid data!: {exc}")
    exc_json = json.loads(exc.json())
    response = {"message": [], "data": None}
    for error in exc_json:
        response['message'].append(f"{error['loc']}: {error['msg']}")

    return JSONResponse(response, status_code=422)

@app.get("/")
async def root():
    return {"message": "Backend Application for RareConnect"}
