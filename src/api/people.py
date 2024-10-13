from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from src.search import build_search_statements, expand_search_statements
from src.order_by import user_sortable_endpoint, SortOption, SortDirection

#from fastapi_pagination import Page, add_pagination, paginate

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError


router = APIRouter(
    prefix="/communities/{c_id}/people",
    tags=["people"],
)


@router.get("/search")
@user_sortable_endpoint(SortOption.Firstname, SortOption.Lastname, SortOption.Username)
def search_people(c_id: int, firstname: str | None = None, lastname: str | None = None, username: str | None = None, sort_by: SortOption | None = SortOption.Firstname, sort_direction: SortDirection | None = SortDirection.Ascending):

    
    #Create a dictionary of the search terms and their corresponding values.
    fieldDict = {
        "firstname": firstname,
        "lastname": lastname,
        "username": username
    }
    binds, search_clauses = build_search_statements(fieldDict)

    try:
        
        with db.engine.begin() as conn:
            people = conn.execute(
                sqlalchemy.text(
                    f"""
                    SELECT user_profiles.id, firstname, lastname, username, role
                    FROM roles
                    INNER JOIN user_profiles ON roles.profile_id = user_profiles.id
                    WHERE community_id = :c_id {expand_search_statements(search_clauses)}
                    ORDER BY role DESC, {sort_by} {sort_direction}
                    """
                ), ({"c_id": c_id} | binds)
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    returnList = []
    for person in people:
        returnList.append(
            {
                "id": person[0],
                "first_name": person[1],
                "last_name": person[2],
                "username": person[3],
                "role": person[4]
            }
        )
    return returnList
