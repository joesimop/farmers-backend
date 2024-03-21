from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation
from typing import Optional
from src.api.search import build_search_statements, expand_search_statements
from src.order_by import user_sortable_endpoint, SortOption, SortDirection


import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError


router = APIRouter(
    prefix="/communities/{c_id}/board",
    tags=["board"],
)

class Comment(BaseModel):
    id: Optional[int] = None
    post_id: int
    profile_id: int
    text: str
    timestamp: datetime.datetime

class BoardPost(BaseModel):
    id: Optional[int] = None
    profile_id: int
    text: str
    timestamp: datetime.datetime
    upvotes: Optional[int] = 0
    upvoted: Optional[bool] = False
    favorited: Optional[bool] = False
    pinned: bool

class BooleanToggle(BaseModel):
    profile_id: Optional[int] = None
    post_id: int
    old_bool_state: bool


def posts_filter(post_type: str):
    if post_type == "pinned":
        return "AND pinned = TRUE"
    elif post_type == "unpinned":
        return "AND pinned = FALSE"
    else:
        return ""
    
@router.get("/posts/{profile_id}")
@router.get("/posts/{profile_id}/{post_type}")
def get_posts(c_id : int, profile_id: int, post_type: str = "all"):
    """
    Retrieve posts and comments for a specific community.

    Parameters:
    - c_id (int): The ID of the community for which posts and comments are to be retrieved.
    - profile_id (int): The ID of the user profile viewing the posts and comments.
    - post_type (str): The type of posts to retrieve. Can be "all", "pinned", or "unpinned".

    Returns:
    - List[dict]: A list of dictionaries representing posts and comments, each containing post details including 'id', 'profile_id', 'username', 'text', 'timestamp', 'upvotes', 'upvoted', 'favorited', 'pinned', and 'comments'.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error". If no posts are found for the specified community, a 404 Not Found status code is returned with the detail "No posts found for this community".

    Implementation Details:
    - The function executes SQL queries to retrieve posts and comments for the specified community.
    - Posts are fetched along with additional information such as the number of upvotes, whether the current user has upvoted or favorited the post, etc.
    - Comments are fetched for each post, limited to the three most recent comments per post.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    - If no posts are found for the specified community, a 404 Not Found is raised with an appropriate error message.
    """

    try:
        with db.engine.begin() as conn:

            posts = conn.execute(
                sqlalchemy.text(
                    f"""
                    WITH s_posts AS (
                        SELECT post_id
                        FROM upvoted_posts
                        WHERE profile_id = :profile_id
                    ),
                    
                    upvote_counts AS (
                        SELECT post_id, COUNT(*) AS upvotes
                        FROM upvoted_posts
                        GROUP BY post_id
                    ),

                    favorited_posts AS (
                        SELECT post_id
                        FROM favorited_posts
                        WHERE profile_id = :profile_id
                    ),

                    comment_counts AS ( 
                        SELECT post_id, COUNT(*) AS total_comments
                        FROM comments
                        GROUP BY post_id
                    )

                    SELECT posts.id AS id, username, profile_id, text, COALESCE(upvote_counts.upvotes, 0) as upvotes, COALESCE(comment_counts.total_comments, 0) as total_comments, timestamp, pinned,
                    CASE WHEN s_posts.post_id IS NOT NULL THEN TRUE ELSE FALSE END AS upvoted,
                    CASE WHEN favorited_posts.post_id IS NOT NULL THEN TRUE ELSE FALSE END AS favorited
                    FROM posts
                    JOIN user_profiles ON posts.profile_id = user_profiles.id
                    LEFT JOIN upvote_counts ON posts.id = upvote_counts.post_id
                    LEFT JOIN s_posts ON posts.id = s_posts.post_id
                    LEFT JOIN favorited_posts ON posts.id = favorited_posts.post_id
                    LEFT JOIN comment_counts ON posts.id = comment_counts.post_id
                    WHERE community_id = :community_id {posts_filter(post_type)}
                    ORDER BY timestamp DESC;
                    """
                ), ({"community_id" : c_id, "profile_id" : profile_id} )
            ).fetchall()

            comments =  conn.execute(
                sqlalchemy.text(
                    """
                    SELECT numbered_comments.id, numbered_comments.post_id, username, numbered_comments.profile_id, numbered_comments.text, numbered_comments.timestamp
                    FROM (
                        SELECT id, post_id, profile_id, text, timestamp,
                        ROW_NUMBER() OVER (PARTITION BY post_id ORDER BY timestamp ASC) AS row_number
                        FROM comments
                    ) as numbered_comments
                    JOIN user_profiles ON numbered_comments.profile_id = user_profiles.id
                    WHERE row_number <= 3
                    ORDER BY post_id DESC, timestamp ASC
                    """
                ), ({"community_id" : c_id } )
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
        
    if posts is None:
        raise(HTTPException(status_code=404, detail="No posts found for this community"))
    
    returnList = []
    for post in posts:
        returnList.append({
            "id" : post.id,
            "profile_id" : post.profile_id,
            "username" : post.username,
            "text" : post.text,
            "timestamp" : post.timestamp.isoformat(timespec="seconds"),
            "upvotes" : post.upvotes,
            "upvoted" : post.upvoted,
            "favorited" : post.favorited,
            "pinned" : post.pinned,
            "comment_count" : post.total_comments,
            "comments": [
                    {
                        "id" : comment.id,
                        "username" : comment.username,
                        "profile_id" : comment.profile_id,
                        "post_id" : comment.post_id,
                        "text" : comment.text,
                        "timestamp" : comment.timestamp.isoformat(timespec="seconds")
                    }
                    for comment in comments if comment.post_id == post.id
                ]
            }
        )

    return JSONResponse(content=returnList, status_code=200)

@router.post("/post")
def create_post(c_id : int, post: BoardPost):
    """
    Creates a new post for the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to create the post for.
    - post (BoardPost): The post object containing information such as profile_id, text, timestamp, upvoted, pinned

    Returns:
    - 201: If the post is successfully created.

    Raises:
    - HTTPException 400: If the post is invalid.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Insert a new post into the posts table.
    - If the post is invalid, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:
            
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO posts (community_id, profile_id, text, timestamp, upvotes, pinned)
                    VALUES (:community_id, :profile_id, :text, :timestamp, :upvotes, :pinned)
                    """
                ), ({"community_id" : c_id,
                    "profile_id" : post.profile_id,
                    "text" : post.text,
                    "timestamp" : post.timestamp,
                    "upvotes" : 0,
                    "pinned" : post.pinned})
            )

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201

@router.put("/upvote_toggle")
def upvote_post(c_id : int, input: BooleanToggle):
    """
    Upvotes or un-upvotes a post for the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to upvote the post for.
    - input (BooleanToggle): The object containing the profile_id, post_id, and current_bool_state.

    Returns:
    - 201: If the post is successfully upvote or un-upvoted.

    Raises:
    - HTTPException 400: If the post does not exist.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Insert a new upvote into the upvoted_posts table if current_bool_state is True, otherwise delete the upvote.
    - If the post does not exist, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:
            
            if input.old_bool_state:
                conn.execute(
                    sqlalchemy.text(
                        """
                        DELETE FROM upvoted_posts
                        WHERE profile_id = :profile_id AND post_id = :post_id
                        """
                    ), ({"profile_id" : input.profile_id, "post_id" : input.post_id})
                )
            else:
                conn.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO upvoted_posts (profile_id, post_id)
                        VALUES (:profile_id, :post_id)
                        """
                    ), ({"profile_id" : input.profile_id, "post_id" : input.post_id})
                )
                

    except DBAPIError as error:
        if isinstance(error.orig, ForeignKeyViolation):
            raise(HTTPException(status_code=400, detail="Post does not exist"))
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201


@router.put("/favorite_toggle")
def favorite_post(c_id : int, input: BooleanToggle):
    """
    Favorites or un-favorites a post for the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to favorite the post for.
    - input (BooleanToggle): The object containing the profile_id, post_id, and current_bool_state.

    Returns:
    - 201: If the post is successfully favorited or un-favorited.

    Raises:
    - HTTPException 400: If the post does not exist.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Insert a new favorite into the favorited_posts table if current_bool_state is True, otherwise delete the favorite.
    - If the post does not exist, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:
            
            if input.old_bool_state:
                conn.execute(
                    sqlalchemy.text(
                        """
                        DELETE FROM favorited_posts
                        WHERE profile_id = :profile_id AND post_id = :post_id
                        """
                    ), ({"profile_id" : input.profile_id, "post_id" : input.post_id})
                )
            else:
                conn.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO favorited_posts (profile_id, post_id)
                        VALUES (:profile_id, :post_id)
                        """
                    ), ({"profile_id" : input.profile_id, "post_id" : input.post_id})
                )
                

    except DBAPIError as error:
        if isinstance(error.orig, ForeignKeyViolation):
            raise(HTTPException(status_code=400, detail="Post does not exist"))
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201

@router.put("/pin_toggle/{post_id}")
def pin_post(c_id : int, post_id: int):
    """
    Pins or unpins a post for the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to pin the post for.
    - input (PinToggle): The object containing the profile_id, post_id, and pin_state.

    Returns:
    - 201: If the post is successfully pinned or unpinned.

    Raises:
    - HTTPException 400: If the post does not exist.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Update the pinned column of the post in the posts table.
    - If the post does not exist, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:
            
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE posts
                    SET pinned = NOT pinned
                    WHERE community_id = :c_id AND id = :post_id
                    """
                ), ({"c_id": c_id,  "post_id" : post_id})
            )

    except DBAPIError as error:
        if isinstance(error.orig, ForeignKeyViolation):
            raise(HTTPException(status_code=400, detail="Post does not exist"))
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201

@router.post("/comment")
def create_comment(c_id : int, comment: Comment):
    """
    Creates a new comment for the post designated by post_id.

    Parameters:
    - c_id (int): The ID of the community to create the comment for.
    - comment (Comment): The comment object containing information such as profile_id, text, timestamp

    Returns:
    - 201: If the comment is successfully created.

    Raises:
    - HTTPException 400: If the comment is invalid.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Insert a new comment into the comments table.
    - If the comment is invalid, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:
            
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO comments (post_id, profile_id, text, timestamp)
                    VALUES (:post_id, :profile_id, :text, :timestamp)
                    """
                ), ({"post_id" : comment.post_id,
                    "profile_id" : comment.profile_id,
                    "text" : comment.text,
                    "timestamp" : comment.timestamp})
            )

    except DBAPIError as error:
        if isinstance(error.orig, ForeignKeyViolation):
            raise(HTTPException(status_code=400, detail="Post does not exist"))
        
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201

@router.get("/comments/{post_id}")
def get_comments(c_id : int, post_id: int):
    """
    Get all comments from the post designated by post_id.

    Parameters:
    - c_id (int): The ID of the community to get the comments from.
    - post_id (int): The ID of the post to get the comments from.

    Returns:
    - A list of comments from the post designated by post_id.

    Raises:
    - HTTPException 404: If no comments are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all comments from the post designated by post_id.
    - If no comments are found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            comments = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT comments.id, comments.post_id, username, profile_id, text, timestamp
                    FROM comments
                    JOIN user_profiles ON comments.profile_id = user_profiles.id
                    WHERE post_id = :post_id
                    """
                ), ({"post_id" : post_id})
            ).fetchall()

    except DBAPIError as error:
        raise(HTTPException(status_code=500, detail="Database error"))
        
    if comments is None:
        raise(HTTPException(status_code=404, detail="No comments found for this post"))
    
    returnList = []
    for comment in comments:
        returnList.append({
            "id" : comment.id,
            "username" : comment.username,
            "profile_id" : comment.profile_id,
            "post_id" : comment.post_id,
            "text" : comment.text,
            "timestamp" : comment.timestamp.isoformat(timespec="seconds")
        })
    
    return JSONResponse(content=returnList, status_code=200)


@router.get("/search")
@user_sortable_endpoint(SortOption.Date, SortOption.Pinned, SortOption.Username)
def search_posts(c_id: int, username: str | None = None, body: str | None = None, sort_by: SortOption | None = SortOption.Date, sort_direction: SortDirection | None = SortDirection.Descending):

    #Create a dictionary of the search terms and their corresponding values.
    fieldDict = {
        "username": username,
        "text": body
    }
    binds, search_clauses = build_search_statements(fieldDict)
    
    try:
        with db.engine.begin() as conn:
            posts = conn.execute(
                sqlalchemy.text(
                    f"""
                    SELECT posts.id, username, profile_id, text, timestamp, pinned
                    FROM posts
                    JOIN user_profiles ON posts.profile_id = user_profiles.id
                    WHERE community_id = :c_id {expand_search_statements(search_clauses)}
                    ORDER BY {sort_by} {sort_direction}
                    """
                ), ({"c_id": c_id} | binds)
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    returnList = []
    for post in posts:
        returnList.append(
            {
                "id": post.id,
                "username": post.username,
                "profile_id": post.profile_id,
                "text": post.text,
                "timestamp": post.timestamp.isoformat(timespec="seconds"),
                "pinned": post.pinned
            }
        )

    return returnList