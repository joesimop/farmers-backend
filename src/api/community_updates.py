import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from src.api.search import build_search_statements, expand_search_statements
from src.order_by import user_sortable_endpoint, SortOption, SortDirection

import sqlalchemy
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_profiles, community_requests
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/communities/{c_id}/community_updates",
    tags=["community_updates"],
)

#Optional fields are for the values that are created on generation
class Article(BaseModel):
    id: Optional[int] = None
    title: str
    abstract: Optional[str] = None
    content: str
    timestamp: Optional[datetime.datetime] = None



@router.get("/search")
@user_sortable_endpoint(SortOption.Date, SortOption.Title)
def search_articles(c_id: int, title: str | None = None, abstract: str | None = None, sort_by: SortOption | None = SortOption.Date, sort_direction: SortDirection | None = SortDirection.Descending):
    """
    Searches for articles in the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to search for articles in.
    - title (str): The title of the article to search for.
    - abstract (str): The abstract of the article to search for.
    - content (str): The content of the article to search for.

    Returns:
    - A list of articles that match the search criteria.

    Raises:
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Search for articles in the community designated by c_id.
    - If there is a database error, raise an error.
    """

    #Create a dictionary of the search terms and their corresponding values.
    fieldDict = {
        "title": title,
        "abstract": abstract
    }
    binds, search_clauses = build_search_statements(fieldDict)

    try:
        with db.engine.begin() as conn:
            articles = conn.execute(
                sqlalchemy.text(
                    f"""
                    SELECT id, title, abstract, timestamp
                    FROM community_updates
                    WHERE community_id = :c_id {expand_search_statements(search_clauses)}
                    ORDER BY {sort_by} {sort_direction}
                    """
                ), ({"c_id": c_id} | binds)
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
        
    returnList = []
    for article in articles:
        returnList.append(
            {
                "id": article[0],
                "title": article[1],
                "abstract": article[2],
                "timestamp": article[3].isoformat(timespec="seconds")
            }
        )
    return returnList


@router.get("/all")
def get_article_thumbnails(c_id : int):
    """
    Gets all article thumbnails from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to get the article thumbnails from.

    Returns:
    - A list of article thumbnails from the community designated by c_id.

    Raises:
    - HTTPException 404: If no article thumbnails are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all article thumbnails from the community designated by c_id.
    - If no article thumbnails are found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            articles = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT id, title, abstract, timestamp
                    FROM community_updates
                    WHERE community_id = :community_id
                    ORDER BY timestamp DESC
                    """
                ), ({"community_id" : c_id}
                )
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
        
    if articles is None:
        raise(HTTPException(status_code=404, detail="No articles found for this community"))
    
    returnList = []
    for article in articles:
        returnList.append(
            {
                "id": article[0],
                "title": article[1],
                "abstract": article[2],
                "timestamp": article[3].isoformat(timespec="seconds")
            }
        )
    return returnList

@router.get("/{article_id}")
def get_article(c_id : int, article_id: int):
    """
    Gets the article designated by article_id from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to get the article from.
    - article_id (int): The ID of the article to get.

    Returns:
    - The article designated by article_id from the community designated by c_id.

    Raises:
    - HTTPException 404: If no article is found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get the article designated by article_id from the community designated by c_id.
    - If no article is found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            article = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT title, abstract, content, timestamp
                    FROM community_updates
                    WHERE id = :article_id AND community_id = :community_id
                    """
                ), ({"article_id" : article_id,
                    "community_id" : c_id}
                )
            ).one_or_none()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
        
    if article is None:
        raise(HTTPException(status_code=404, detail="No article found for this community"))
    

    returnObject = {
        "title": article.title,
        "abstract": article.abstract,
        "content": article.content,
        "timestamp": article.timestamp.isoformat(timespec="seconds")
    }

    return returnObject


@router.post("/submit")
def submit_article(c_id : int, article: Article):
    """
    Submits a new article to the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to submit the article to.
    - article (Article): The article to submit.

    Returns:
    - A JSONResponse with a status code of 200.
    """
    try:
        with db.engine.begin() as conn:
            
            conn.execute(
                sqlalchemy.text(
                        """
                        INSERT INTO community_updates (community_id, title, abstract, content, timestamp)
                        VALUES (:community_id, :title, :source, :abstract, :content, :timestamp)
                        """
                ), ({"community_id" : c_id,
                    "title" : article.title,
                    "abstract" : article.abstract,
                    "content" : article.content
                    })
            )

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 200

@router.delete("/{article_id}")
def delete_article(c_id : int, article_id: int):
    """
    Deletes the article designated by article_id from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to delete the article from.
    - article_id (int): The ID of the article to delete.

    Returns:
    - A JSONResponse with a status code of 200.

    Raises:
    - HTTPException 404: If no article is found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Delete the article designated by article_id from the community designated by c_id.
    - If no article is found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            conn.execute(
                sqlalchemy.text(
                    """
                    DELETE FROM community_updates
                    WHERE id = :article_id AND community_id = :community_id
                    """
                ), ({"article_id" : article_id,
                    "community_id" : c_id}
                )
            )

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
        
    return 200