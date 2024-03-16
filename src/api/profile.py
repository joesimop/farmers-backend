from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_credentials, user_profiles, communities
from src import hashing
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)

class UserCredentials(BaseModel):
    username: str
    password: str
    
class UserStorage(BaseModel):
    salt: bytes
    pw_hash: bytes


class Profile(BaseModel):
    id: int
    firstname: str
    lastname: str
    username: str
    password: str
    email: str
    gender: str
    age: str
    residingcity: str

class CommunityRequest(BaseModel):
    community_id: int
    name: str
    request_status: str
    submit_date: datetime.datetime



@router.get("/community_profile/{c_id}/{profile_id}")
def get_user_by_id(c_id: int, profile_id: int):
    
    try:
        with db.engine.begin() as conn:
            user = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT user_profiles.id, firstname, lastname, username, email, residingcity, joined, role
                    FROM user_profiles
                    JOIN roles ON user_profiles.id = roles.profile_id
                    WHERE user_profiles.id = :profile_id AND roles.community_id = :c_id
                    """
                ), ({"profile_id": profile_id, "c_id": c_id})
            ).first()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    jsonObject = {
        "id": user[0],
        "firstname": user[1],
        "lastname": user[2],
        "username": user[3],
        "email": user[4],
        "residingcity": user[5],
        "joined": user[6].isoformat(timespec="seconds"),
        "role": user[7]
    }

    return JSONResponse(content=jsonObject, status_code=200)


# Get endpoint to get a user by username
@router.get("/{username}")
def get_user_by_username(username: str):
        
        
        with db.engine.begin() as conn:
    
            result = conn.execute(
                sqlalchemy.select(user_profiles.c.id,
                                user_profiles.c.firstname,
                                user_profiles.c.lastname,
                                user_profiles.c.username,
                                user_profiles.c.email,
                                user_profiles.c.gender,
                                user_profiles.c.age,
                                user_profiles.c.residingcity
                                )
                .where(user_profiles.c.username == username)
            ).first()

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        jsonObject = {
            "id": result[0],
            "firstname": result[1],
            "lastname": result[2],
            "username": result[3],
            "email": result[4],
            "gender": result[5],
            "age": result[6],
            "residingcity": result[7]
        }

        return JSONResponse(content=jsonObject, status_code=200)

@router.get("/{profile_id}/communities")
def get_user_communities(profile_id: int):
    """
    Gets all communities that the user is a part of.

    Parameters:
    - id (int): The ID of the user to get the communities from.

    Returns:
    - A list of community IDs that the user is a part of.

    Raises:
    - HTTPException 404: If no communities are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all communities that the user is a part of.
    - If no communities are found, don't raise an error, just return an empty list.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            communityList = conn.execute(
                sqlalchemy.select(
                    roles.c.community_id,
                    communities.c.name,
                    roles.c.role
                ).select_from(roles.join(user_profiles, user_profiles.c.id == roles.c.profile_id)
                                    .join(communities, communities.c.id == roles.c.community_id))
                .where(user_profiles.c.id == profile_id)
            ).fetchall()

    except DBAPIError as error:
        raise(HTTPException(status_code=500, detail="Database error"))

    returnList = []
    for entry in communityList:
        returnList.append(
            {
                "id": entry[0],
                "name": entry[1],
                "role": entry[2]
            }
        )
    return returnList

# Create endpoint is ONLY to create a new user

@router.post("/create")
def create_profile(profile: Profile):
    """
    Creates a new user.

    Parameters:
    - user (User): The user object containing information such as 
        username, password, firstname, lastname, email, gender, age, and residingcity.

    Returns:
    - int: HTTP status code 201 indicating successful creation.

    Raises:
    - HTTPException: If the provided username already exists, a 400 Bad Request status code is returned with the detail "Username already exists."
    - DBAPIError: If there is an error during database interaction, it is caught, and an appropriate error message is printed.

    Implementation Details:
    - The function hashes the password and stores the salt and hash in the database.
    - It first creates user credentials, ensuring the username is unique.
    - The ID of the created user credentials is retrieved.
    - A new user profile is created with the associated user credentials.
    """

    # Hash the password and store the salt and hash in the database
    salt, pw_hash = hashing.hash_new_password(profile.password)

    #First create the user credentials, make sure the username is unique
    try:
        with db.engine.begin() as conn:

            #Get the id of the created user credentials
            credentials_id = conn.execute(
                sqlalchemy
                .insert(user_credentials)
                .values(salt=salt, pw_hash=pw_hash)
                .returning(user_credentials.c.id)
            ).fetchall()[0][0]

            #Create the new user's profile, with associated user credentials
            conn.execute(
                sqlalchemy
                .insert(user_profiles)
                .values(credentials_id=credentials_id,
                        username=profile.username,
                        firstname=profile.firstname, 
                        lastname=profile.lastname, 
                        email=profile.email, 
                        gender=profile.gender,
                        age=int(profile.age),
                        residingcity=profile.residingcity)
                .returning(user_profiles.c.id)
            )


    except DBAPIError as error:

        if isinstance(error.orig, UniqueViolation):

            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        print("Error: ", error)
        
    #Return "Created" status code
    return 201

#  Authroize endpoint is ONLY to verify user credentials, so no other part of the 
#  database is accessed. Once, authroized, the user can access other endpoints
@router.post("/authorize")
def verify_user(user: UserCredentials):
    """
    Verifies user credentials for authentication.

    Parameters:
    - user (UserCredentials): username and password.

    Returns:
    - int: HTTP status code 200 if authentication is successful.

    Raises:
    - HTTPException: If the provided username does not exist, a 400 Bad Request status code is returned with the detail "Username does not exist."
                     If the provided password is incorrect, a 400 Bad Request status code is returned with the detail "Incorrect password."

    Implementation Details:
    - The function queries the database to retrieve the salt and hash associated with the provided username.
    - If the username does not exist, a 400 Bad Request is raised.
    - The function compares the provided password with the stored hash using the stored salt.
    - If the password is correct, a 200 OK status code is returned.
    - If the password is incorrect, a 400 Bad Request is raised.
    """

    with db.engine.begin() as conn:

        user_storage = conn.execute(
            sqlalchemy
            .select(user_credentials.c.salt, user_credentials.c.pw_hash)
            .select_from(user_profiles.join(user_credentials, 
                                            user_profiles.c.credentials_id == user_credentials.c.id))
            .where(user_profiles.c.username == user.username)
        ).first()

        if user_storage is None:

            raise HTTPException(
                status_code=400,
                detail="Username does not exist"
            )

        salt = user_storage[0]
        pw_hash = user_storage[1]

        if hashing.is_correct_password(salt, pw_hash, user.password):
            return 200

        else:
            raise HTTPException(
                status_code=400,
                detail="Incorrect password"
            )
        
@router.get("/{profile_id}/community_requests")
def get_community_requests(profile_id: int):

    try:
        with db.engine.begin() as conn:

            requests = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT community_requests.community_id, communities.name, community_requests.status, community_requests.request_date    
                    FROM community_requests
                    JOIN communities ON communities.id = community_requests.community_id
                    WHERE community_requests.profile_id = :profile_id
                    """
                ), ({"profile_id": profile_id})
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    returnList = []
    for entry in requests:
        returnList.append(
            {
                "id": entry[0],
                "name": entry[1],
                "status": entry[2],
                "submit_date": entry[3].isoformat(timespec="seconds")
            }
        )

    return returnList