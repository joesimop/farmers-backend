from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation, UniqueViolation

import sqlalchemy
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_profiles, community_requests
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/communities/{c_id}/guidelines",
    tags=["guidelines"],
)

class GuidelineCreation(BaseModel):
    order_number: int
    text: str

class Guideline(BaseModel):
    id : int
    order_number: int
    text: str

@router.get("/all")
def get_guidelines(c_id: int):

    """
    Retrieve guidelines for a specific community.

    Parameters:
    - c_id (int): The ID of the community for which guidelines are to be retrieved.

    Returns:
    - List[dict]: A list of dictionaries representing guidelines, each containing 'order_number' and 'text'.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error."

    Implementation Details:
    - The function queries the database to retrieve guidelines for the specified community.
    - Each dictionary represents a guideline with keys 'order_number' and 'text'.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    """

    try:
        with db.engine.begin() as conn:

            guidelines = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT id, order_number, text
                    FROM guidelines
                    WHERE community_id = :community_id
                    ORDER BY order_number
                    """
                ), ({"community_id" : c_id})
            ).fetchall()

    except DBAPIError as error:
            
            raise(HTTPException(status_code=500, detail="Database error"))
    
    returnList = []
    for guideline in guidelines:
        returnList.append({
            "id" : guideline[0], 
            "order_number": guideline[1],
            "text": guideline[2]
        })
    
    return returnList


@router.post("/new")
def new_guideline(c_id : int, guideline: GuidelineCreation):

    """
    Create a new guideline for a specific community.

    Parameters:
    - c_id (int): The ID of the community for which the guideline is to be created.
    - guideline (Guideline): The guideline object containing 'order_number' and 'text'.

    Returns:
    - int: HTTP status code 201 indicating successful creation.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error."
    - HTTPException: If the order number already exists, a 400 Bad Request status code is returned with the detail "Order number already exists."

    Implementation Details:
    - The function inserts a new guideline into the database for the specified community.
    - The guideline information includes the provided community ID, order number, and text.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    - Returns HTTP status code 201 upon successful creation of the guideline.
    """
     
    try:
        with db.engine.begin() as conn:

            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO guidelines (community_id, order_number, text)
                    VALUES (:community_id, :order_number, :text)
                    """
                ), ({"community_id" : c_id, "order_number" : guideline.order_number, "text" : guideline.text})
            )

    except DBAPIError as error:

        if isinstance(error.orig, UniqueViolation):
            raise HTTPException(
                status_code=400,
                detail="Order number already exists"
            )
        
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201


@router.get("/reorder/{guideline_id}/{from_order}/{to_order}")
def reorder_guideliens(c_id: int, guideline_id : int, from_order: int, to_order : int):
    
    """
    Reorder guidelines within a specific community.

    Parameters:
    - c_id (int): The ID of the community to which the guidelines belong.
    - guideline_id (int): The ID of the guideline to be moved.
    - from_order (int): The current order number of the guideline to be moved.
    - to_order (int): The desired order number for the guideline.

    Returns:
    - int: HTTP status code 200 indicating a successful reorder.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error."

    Implementation Details:
    - The function updates the order numbers of guidelines between `from_order` and `to_order`.
    - If `from_order` is less than `to_order`, it decrements the order numbers in the specified range.
    - If `from_order` is greater than `to_order`, it increments the order numbers in the specified range.
    - The order number of the guideline being moved is updated to the specified `to_order`.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    - Returns HTTP status code 200 upon successful reorder.
    """
    
    try:
        with db.engine.begin() as conn:

            #Update the order numbers of the guidelines between the from_order and to_order
            if(from_order < to_order):
                conn.execute(
                    sqlalchemy.text(
                        """
                        UPDATE guidelines
                        SET order_number = order_number - 1
                        WHERE community_id = :community_id AND order_number > :from_order AND order_number <= :to_order
                        """
                    ), ({"community_id" : c_id, "from_order" : from_order, "to_order" : to_order})
                )
            else:
                conn.execute(
                    sqlalchemy.text(
                        """
                        UPDATE guidelines
                        SET order_number = order_number + 1
                        WHERE community_id = :community_id AND order_number < :from_order AND order_number >= :to_order
                        """
                    ), ({"community_id" : c_id, "from_order" : from_order, "to_order" : to_order})
                )


            #Update the order number of the guideline being moved
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE guidelines
                    SET order_number = :order_number
                    WHERE id = :guideline_id
                    """
                ), ({"order_number" : to_order, "guideline_id" : guideline_id})
            )

    except DBAPIError as error:
        print(error)
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 200


@router.delete("/delete/{guideline_id}")
def delete_guideline(guideline_id : int):

    """
    Delete a guideline from the database.

    Parameters:
    - guideline_id (int): The ID of the guideline to be deleted.

    Returns:
    - int: HTTP status code 200 indicating successful deletion.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error."

    Implementation Details:
    - The function deletes the guideline from the database.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    - Returns HTTP status code 200 upon successful deletion of the guideline.
    """
    
    try:
        with db.engine.begin() as conn:

            #Update order numbers of guidelines after the about to be deleted guideline
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE guidelines
                    SET order_number = order_number - 1
                    WHERE order_number > (SELECT order_number FROM guidelines WHERE id = :guideline_id)
                    """
                ), ({"guideline_id" : guideline_id})
            )

            #Delete the guideline
            conn.execute(
                sqlalchemy.text(
                    """
                    DELETE FROM guidelines
                    WHERE id = :guideline_id
                    """
                ), ({"guideline_id" : guideline_id})
            )

            

    except DBAPIError as error:

        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 200

@router.patch("/update")
def update_guideline(guideline : Guideline):

    """
    Update a guideline in the database.

    Parameters:
    - guideline (Guideline): The guideline object containing the ID of the guideline to be updated, the new order number, and the new text.

    Returns:
    - int: HTTP status code 200 indicating successful update.

    Raises:
    - HTTPException: If there is an error during database interaction, a 500 Internal Server Error status code is returned with the detail "Database error."

    Implementation Details:
    - The function updates the order number and text of the guideline in the database.
    - If there is a database error, a 500 Internal Server Error is raised with an appropriate error message.
    - Returns HTTP status code 200 upon successful update of the guideline.
    """
    
    try:
        with db.engine.begin() as conn:

            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE guidelines
                    SET text = :text
                    WHERE id = :guideline_id
                    """
                ), ({ "guideline_id" : guideline.id, "text" : guideline.text})
            )

    except DBAPIError as error:

        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 200
