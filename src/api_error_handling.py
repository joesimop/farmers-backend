import sys
from psycopg2.errors import ForeignKeyViolation, UniqueViolation, NotNullViolation, CheckViolation
from fastapi import HTTPException
from typing import Optional
from enum import Enum

class DatabaseError(Enum):
    FOREIGN_KEY_VIOLATION = 1
    UNIQUE_VIOLATION = 2
    NOT_NULL_VIOLATION = 3
    CHECK_VIOLATION = 4

def foreign_key_violation_exception(err):
    if isinstance(err, ForeignKeyViolation):
        raise HTTPException(status_code=404, detail=err.diag.message_detail)
    
def unique_violation_exception(err):
    if isinstance(err, UniqueViolation):
        raise HTTPException(status_code=409, detail=err.diag.message_detail)
    
def not_null_violation_exception(err):
    if isinstance(err, NotNullViolation):
        raise HTTPException(status_code=400, detail=err.diag.message_detail)
    
def check_violation_exception(err):
    if isinstance(err, CheckViolation):
        raise HTTPException(status_code=400, detail=err.diag.message_detail)


def handle_error(err, *types: list[DatabaseError]):
    """
    Raises an HTTPException, checking for errors in the types list.
    """

    for error_type in types:
        if error_type == DatabaseError.FOREIGN_KEY_VIOLATION:
            foreign_key_violation_exception(err.orig)
        elif error_type == DatabaseError.UNIQUE_VIOLATION:
            unique_violation_exception(err.orig)
        elif error_type == DatabaseError.NOT_NULL_VIOLATION:
            not_null_violation_exception(err.orig)
        elif error_type == DatabaseError.CHECK_VIOLATION:
            check_violation_exception(err.orig)
        
        