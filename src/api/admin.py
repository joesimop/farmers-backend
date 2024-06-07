from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.api import auth
from enum import Enum

import sqlalchemy
import datetime
from pydantic import BaseModel
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/{c_id}/admin",
    tags=["admin"]
)

class AllowPost(BaseModel):
    notification_id: int
    allowed: bool

class AdminNotification(Enum):
    join_request = "join_request"
    flagged_post = "flagged_post"
    member_joined = "member_joined"


@router.get("/notifications")
def get_all_notifications(c_id : int):
    """
    Get all notifications for the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to get notifications for.

    Returns:
    - A list of notifications for the community designated by c_id.

    Raises:
    - HTTPException 404: If no notifications are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all notifications for the community designated by c_id.
    - If no notifications are found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            notifications = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT id, type, text, timestamp
                    FROM admin.notifications
                    WHERE community_id = :community_id
                    """
                ), ({"community_id" : c_id}
                )
            ).fetchall()

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    if notifications is None:
        raise(HTTPException(status_code=404, detail="No notifications found"))
    
    returnList = []
    for notification in notifications:
        returnList.append({
            "id": notification[0],
            "type": notification[1],
            "text": notification[2],
            "timestamp": notification[3].isoformat(timespec="seconds")
        })

    return returnList

@router.post("/permit_post")
def permit_post(c_id : int, post: AllowPost):
    """
    Permit a post designated by post_id.

    Parameters:
    - c_id (int): The ID of the community to permit the post in.
    - post (AllowPost): The ID of the post to permit.

    Returns:
    - A success message if the post is permitted.

    Raises:
    - HTTPException 404: If the post is no  t found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Permit the post designated by post_id.
    - If the post is not found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:
            #Delete post no matter what
            permitted_post = conn.execute(
                    sqlalchemy.text(
                        """
                        DELETE FROM admin.notifications
                        WHERE id = :notification
                        returning text, timestamp, profile_id
                        """
                    ), ({"notification" : post.notification_id}
                    )
                ).fetchone()

            if post.allowed:
                if permitted_post is None:
                    raise(HTTPException(status_code=404, detail="Post not found"))
                else:
                    conn.execute(
                            sqlalchemy.text(
                                """
                                INSERT INTO posts (community_id, profile_id, text, timestamp, upvotes, pinned)
                                VALUES (:community_id, :profile_id, :text, :timestamp, :upvotes, :pinned)
                                """
                            ), ({"community_id" : c_id,
                                "profile_id" : permitted_post.profile_id,
                                "text" : permitted_post.text,
                                "timestamp" : permitted_post.timestamp,
                                "upvotes" : 0,
                                "pinned" : False})
                        )
            else:
                ##TODO: Notify user that their post was not permitted
                print("Post not permitted")

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return {"message": "Post permitted"}
