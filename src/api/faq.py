from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from psycopg2.errors import ForeignKeyViolation, UniqueViolation

import sqlalchemy
from pydantic import BaseModel
from src import database as db
from src.schemas import roles, user_profiles, community_requests
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/communities/{c_id}/faq",
    tags=["faq"],
)

class FAQ(BaseModel):
    id: Optional[int] = None
    order_number: int
    question: str
    answer: str

@router.get("/all")
def get_all_faqs(c_id: int):
    """
    Gets all FAQs from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to get the FAQs from.

    Returns:
    - A list of FAQs from the community designated by c_id.

    Raises:
    - HTTPException 404: If no FAQs are found.
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Get all FAQs from the community designated by c_id.
    - If no FAQs are found, raise an error.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            faqs = conn.execute(
                sqlalchemy.text(
                    """
                    SELECT id, order_number, question, answer
                    FROM frequently_asked_questions
                    WHERE community_id = :community_id
                    ORDER BY order_number
                    """
                ), ({"community_id" : c_id}
                )
            ).fetchall()

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
        
    
    if faqs is None:
        raise(HTTPException(status_code=404, detail="No FAQs found for this community"))
    
    returnList = []
    for faq in faqs:
        returnList.append({
            "id" : faq.id,
            "order_number" : faq.order_number,
            "question" : faq.question,
            "answer" : faq.answer
        })
    return returnList

@router.post("/submit")
def submit_faq(c_id: int, faq: FAQ):
    """
    Submits a new FAQ to the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to submit the FAQ to.
    - faq (FAQ): The FAQ to submit.

    Returns:
    - A JSONResponse with a status code of 200.

    Raises:
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Insert the new FAQ into the database.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO frequently_asked_questions (community_id, order_number, question, answer)
                    VALUES (:community_id, :order_number, :question, :answer)
                    """
                ), ({"community_id" : c_id,
                    "order_number" : faq.order_number,
                    "question" : faq.question,
                    "answer" : faq.answer})
            )

    except DBAPIError as error:
        
        if isinstance(error.orig, UniqueViolation):
            raise(HTTPException(status_code=400, detail="Order Number already exists"))

        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 201

@router.delete("/delete/{faq_id}")
def delete_faq(c_id: int, faq_id: int):
    """
    Deletes the FAQ designated by faq_id from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to delete the FAQ from.
    - faq_id (int): The ID of the FAQ to delete.

    Returns:
    - A JSONResponse with a status code of 200.

    Raises:
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Delete the FAQ from the database.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            #Update the order numbers of the faq after the deleted faq
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE frequently_asked_questions
                    SET order_number = order_number - 1
                    WHERE community_id = :community_id AND order_number > (SELECT order_number FROM frequently_asked_questions WHERE id = :faq_id)
                    """
                ), ({"community_id" : c_id, "faq_id" : faq_id})
            )

            conn.execute(
                sqlalchemy.text(
                    """
                    DELETE FROM frequently_asked_questions
                    WHERE id = :faq_id
                    AND community_id = :community_id
                    """
                ), ({"faq_id" : faq_id,
                    "community_id" : c_id})
            )

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 200

@router.get("/reorder/{faq_id}/{from_order}/{to_order}")
def reorder_faq(c_id: int, faq_id: int, from_order: int, to_order: int):
    """
    Reorders the FAQ designated by faq_id from the community designated by c_id.

    Parameters:
    - c_id (int): The ID of the community to reorder the FAQ from.
    - faq_id (int): The ID of the FAQ to reorder.
    - from_offset (int): The original order number of the FAQ.
    - to_offset (int): The new order number of the FAQ.

    Returns:
    - A JSONResponse with a status code of 200.

    Raises:
    - HTTPException 500: If there is a database error.

    Implementation Details:
    - Reorder the FAQ in the database.
    - If there is a database error, raise an error.
    """

    try:
        with db.engine.begin() as conn:

            #Update the order numbers of the faq between the from_order and to_order
            if(from_order < to_order):
                conn.execute(
                    sqlalchemy.text(
                        """
                        UPDATE frequently_asked_questions
                        SET order_number = order_number - 1
                        WHERE community_id = :community_id AND order_number > :from_order AND order_number <= :to_order
                        """
                    ), ({"community_id" : c_id, "from_order" : from_order, "to_order" : to_order})
                )
            else:
                conn.execute(
                    sqlalchemy.text(
                        """
                        UPDATE frequently_asked_questions
                        SET order_number = order_number + 1
                        WHERE community_id = :community_id AND order_number < :from_order AND order_number >= :to_order
                        """
                    ), ({"community_id" : c_id, "from_order" : from_order, "to_order" : to_order})
                )


            #Update the order number of the guideline being moved
            conn.execute(
                sqlalchemy.text(
                    """
                    UPDATE frequently_asked_questions
                    SET order_number = :order_number
                    WHERE id = :faq_id
                    """
                ), ({"order_number" : to_order, "faq_id" : faq_id})
            )

    except DBAPIError as error:
        
        raise(HTTPException(status_code=500, detail="Database error"))
    
    return 200