from fastapi import FastAPI, exceptions
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from src.api import logs, profile, community, communityspecific, guidelines, donation, communityboard, people, faq, community_updates, admin
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
        "name": "Joseph Simopoulos",
        "email": "joesimop8@gmail.com",
    },
)

app.include_router(profile.router)
app.include_router(community.router)
app.include_router(communityspecific.router)
app.include_router(guidelines.router)
app.include_router(donation.router)
app.include_router(communityboard.router)
app.include_router(people.router)
app.include_router(faq.router)
app.include_router(community_updates.router)
app.include_router(logs.router)
app.include_router(admin.router)

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

        response = {"message": [], "data": None}
        for error in exc_json:
            response['message'].append(f"{error['loc']}: {error['msg']}")

        return JSONResponse(response, status_code=422)

@app.get("/")
async def root():
    return {"message": "Backend Application for Farmer's Market"}
