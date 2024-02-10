from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation, UniqueViolation

import sqlalchemy
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_profiles, community_requests
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/communities/{c_id}",
    tags=["communities"],
)

class CommunityRequest(BaseModel):
    profile_id: int
    message: str


@router.get("/all_profiles")
def get_all_profiles(c_id: int):
    """
    Gets all profiles from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to get the profiles from.

    Returns:
    - A list of abbr_profiles from the community designated by c_id.

    Raises:
    - HTTPException 404: If no profiles are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all profiles from the community designated by c_id.
    - If no profiles are found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            profiles = conn.execute(
                sqlalchemy.select(
                    user_profiles.c.id,
                    user_profiles.c.firstname,
                    user_profiles.c.lastname,
                    user_profiles.c.username
                ).select_from(user_profiles.join(roles, 
                                                 user_profiles.c.id == roles.c.profile_id)
                ).where(roles.c.community_id == c_id)
            ).fetchall()

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
        
    
    if profiles is None:
        raise(HTTPException(status_code=404, detail="No users found"))

    returnList = []
    for entry in profiles:
        returnList.append(
            {
                "id": entry[0],
                "firstname": entry[1],
                "lastname": entry[2],
                "username": entry[3]
            }
        )
    return returnList

@router.get("/{role}")
def get_role(c_id: int, role : str):
    """
    Gets a profiles from the community designated by c_id of type "role".

    Parameters:
    - c_id (int): The ID of the community to get the profiles from.
    - role (str): The role of the profiles to get.

    Returns:
    - A list of abbr_profiles from the community designated by c_id of type "role".

    Raises:
    - HTTPException 404: If no profiles are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all profiles from the community designated by c_id of type "role".
    - If no profiles are found, raise an error.
    - If there is a database error, raise an error.
    """

    # Right off the bat, it role isn't admin or member, raise an error
    if role != "admin" and role != "member":
        raise(HTTPException(status_code=400, detail="Invalid role"))

    try:
        with db.engine.begin() as conn:

            profiles = conn.execute(
                sqlalchemy.select(
                    user_profiles.c.id,
                    user_profiles.c.firstname,
                    user_profiles.c.lastname,
                    user_profiles.c.username
                ).select_from(user_profiles.join(roles, 
                                                 user_profiles.c.id == roles.c.profile_id)
                ).where(roles.c.community_id == c_id, roles.c.role == role)
            ).fetchall()

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
        
    
    if profiles is None:
        raise(HTTPException(status_code=404, detail="No users found"))

    returnList = []
    for entry in profiles:
        returnList.append(
            {
                "id": entry[0],
                "firstname": entry[1],
                "lastname": entry[2],
                "username": entry[3]
            }
        )
    return returnList

@router.post("/request")
def community_request(c_id : int, request : CommunityRequest):
    """
    Sends a request to join the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to send the request to.
    - request (CommunityRequest): The request to send containing the user's profile_id and message.

    Returns:
    - Http Response 201: If the request is successfully created.

    Raises:
    - Http Exception 400: If the Profile or community does not exist.
    - Http Exception 400: If the request already exists.
    - Http Exception 500: If there is a database error.


    Implementation Details:
    - Insert a new request into the requests table.
    - If the profile or community does not exist, raise an error.
    - If the request already exists, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            request_id = conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO community_requests (profile_id, community_id, message)
                    values (:profile_id, :community_id, :message)
                    RETURNING id
                    """
                ), ({"profile_id": request.profile_id, "community_id" : c_id,  "message": request.message})
            ).scalar_one_or_none()

    except DBAPIError as error:

        if isinstance(error.orig, ForeignKeyViolation):

            raise HTTPException(
                status_code=400,
                detail="Profile or community does not exist"
            )
        
        if isinstance(error.orig, UniqueViolation):
            raise HTTPException(
                status_code=400,
                detail="Request already exists"
            )

        print("Error: ", error)
        raise(HTTPException(status_code=500, detail="Database error"))


    return 201