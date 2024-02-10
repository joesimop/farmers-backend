from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation, ForeignKeyViolation

import sqlalchemy
from pydantic import BaseModel
from src import database as db
from src.schemas import communities
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/communities",
    tags=["communities"],
)

class CommunityApplication(BaseModel):
    profile_id: int
    phone_number: str
    professional_email: str
    organization_name: str
    answer1: str
    answer2: str
    message: str

@router.get("/all")
def get_all_communities():
    """
    Retrieve information about all communities.

    Returns:
    - List[dict]: A list of dictionaries representing community information, each containing 'id', 'name', 'abbr_name', and 'join_method'.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error."

    Implementation Details:
    - The function queries the database to retrieve information about all communities.
    - The retrieved information is formatted into a list of dictionaries.
    - Each dictionary represents a community with keys 'id', 'name', 'abbr_name', and 'join_method'.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    """

    try:
        with db.engine.begin() as conn:

            communityList = conn.execute(
                sqlalchemy.select(
                    communities.c.id,
                    communities.c.name,
                    communities.c.abbr,
                    communities.c.join_method
                )
            ).fetchall()

    except DBAPIError as error:
        
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    returnList = []
    for c in communityList:
        returnList.append(
            {
                "id": c[0],
                "name": c[1],
                "abbr": c[2],
                "join_method": c[3]
            }
        )
    
    return returnList


@router.post("/application")
def apply_for_community(application : CommunityApplication):
    """
    Creates a new community application.

    Parameters:
    - application (CommunityApplication): The application object containing information such as profile_id, phone_number, professional_email, organization_name, answer1, answer2, message

    Returns:
    - 201: If the application is successfully created.

    Raises:
    - HTTPException 400: If the user profile is invalid or if the application already exists.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Insert a new application into the community_applications table.
    - If the profile is invalid, raise an error.
    - If the application already exists, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            application_id = conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO community_applications (profile_id, phone_number, professional_email, organization_name, answer1, answer2, message)
                    VALUES (:profile_id, :phone_number, :professional_email, :organization_name, :answer1, :answer2, :message)
                    RETURNING id
                    """
                ), ({"profile_id": application.profile_id, 
                     "phone_number": application.phone_number, 
                     "professional_email": application.professional_email, 
                     "organization_name": application.organization_name, 
                     "answer1": application.answer1, 
                     "answer2": application.answer2,
                     "message": application.message})
            ).scalar_one_or_none()

    except DBAPIError as error:

        if isinstance(error.orig, ForeignKeyViolation):
            raise HTTPException(
                status_code=400,
                detail="Invalid User Profile"
            )
        
        if isinstance(error.orig, UniqueViolation):
            raise HTTPException(
                status_code=400,
                detail="Application already exists"
            )
        
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    if application_id is None:
        raise(HTTPException(status_code=400, detail="Unknown error occurred"))
    
    return 201