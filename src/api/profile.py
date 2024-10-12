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
    first_name: str
    last_name: str
    username: str
    password: str
    email: str
    gender: str
    dob: str
    residing_city: str

class ProfilePost(BaseModel):
    profile_id: int


@router.post("/create")
def create_profile(profile: Profile):
    """
    Creates a new user.

    Parameters:
    - user (User): The user object containing information such as 
        username, password, first_name, last_name, email, gender, age, and residing_city.

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
                sqlalchemy.text(

                )
            ).fetchall()[0][0]

            #Create the new user's profile, with associated user credentials
            conn.execute(
                sqlalchemy.text(
                )
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
            .select(user_credentials.c.salt, user_credentials.c.pw_hash, user_profiles.c.id)
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
        profile_id = user_storage[2]

        if hashing.is_correct_password(salt, pw_hash, user.password):

            #Count the number of logins and logouts
            counts = conn.execute(
            sqlalchemy.text(
                """
                SELECT
                    (SELECT COUNT(*) FROM logs.user_logins WHERE profile_id = :profile_id) as logins,
                    (SELECT COUNT(*) FROM logs.user_logouts WHERE profile_id = :profile_id) as logouts
                """
                ), ({"profile_id": profile_id})
            ).fetchone()

            #If the user is not logged out, raise an error
            if counts.logins != counts.logouts:

                raise HTTPException(
                    status_code=400,
                    detail="Unable to login, user is already logged in."
                )
                
            else:
                #Log the login
                conn.execute(
                    sqlalchemy.text(
                    f"""
                        INSERT INTO logs.user_logins (profile_id)
                        VALUES ({profile_id})
                    """
                    )
                )
                return 200

        else:
            raise HTTPException(
                status_code=400,
                detail="Incorrect password"
            )
        

@router.post("/logout")
def logout(logout: ProfilePost):
    """
    Logs out a user.

    Parameters:
    - profile_id (int): The ID of the user to log out.

    Returns:
    - int: HTTP status code 200 if logout is successful.

    Raises:
    - HTTPException: If the provided profile ID does not exist, a 400 Bad Request status code is returned with the detail "Profile ID does not exist."

    Implementation Details:
    - The function checks if the user is logged in.
    - If the user is not logged in, a 400 Bad Request is raised.
    - The function logs the logout and returns a 200 OK status code.
    """

    with db.engine.begin() as conn:

        #Count the number of logins and logouts
        counts = conn.execute(
            sqlalchemy.text(
                """
                SELECT
                    (SELECT id FROM logs.user_logins WHERE profile_id = :profile_id ORDER BY timestamp DESC LIMIT 1) as most_recent_login_id,
                    (SELECT COUNT(*) FROM logs.user_logins WHERE profile_id = :profile_id) as logins,
                    (SELECT COUNT(*) FROM logs.user_logouts WHERE profile_id = :profile_id) as logouts
                """
            ), ({"profile_id": logout.profile_id})
        ).fetchone()

        #If the user is not logged in, raise an error
        if counts.logins - 1 != counts.logouts:

            raise HTTPException(
                status_code=400,
                detail="Unable to logout, user is not logged in."
            )
        
        else:
            #Otherwise, log the logout, and succesfully let the user logout
            conn.execute(
                sqlalchemy.text(
                """
                    INSERT INTO logs.user_logouts (profile_id, associated_login)
                    VALUES (:profile_id, :most_recent_login_id)
                """
                ), ({"profile_id": logout.profile_id, "most_recent_login_id": counts.most_recent_login_id})
            )

    return 200