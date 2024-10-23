from enum import Enum
from functools import wraps
from fastapi import HTTPException

class SortOption(Enum):
    MarketDate = "MARKET_DATE"
    VendorName = "BUSINESS_NAME"
    Gross = "GROSS"
    FeesPaid = "FEES_PAID"

    def __str__(self):
        return self.value
    
class SortDirection(Enum):
    Ascending = "ASC"
    Descending = "DESC"

    def __str__(self):
        return self.value

def user_sortable_endpoint(*possibleOrderByFields: SortOption):
    def order_by_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            sortBy = kwargs.get("sort_by", None)                                         #Get the sort_by field if it exists
            if sortBy is not None:
                if sortBy not in possibleOrderByFields:                                  #If someone tries to pass something naughty, raise an error
                    raise HTTPException(status_code=400, detail=f"{sortBy} is not available for this endpoint")
                
                sortDirection = kwargs.get("sort_direction", None)                       #Get sort direction if it exists
                if sortDirection is not None:
                    if sortDirection not in SortDirection                 :              #If someone tries to pass something naughty, raise an error
                        raise HTTPException(status_code=400, detail=f"Invalid sort direction: {sortDirection}")
                    
                    sortBy = f"{sortBy}"                                                 #Set the order_by field in kwargs
                    sortDirection = f"{sortDirection}"                                   #Set the sort_direction field in kwargs
                

            return func(*args, **kwargs)
        return wrapper
    return order_by_wrapper