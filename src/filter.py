from ast import List
from functools import wraps
from fastapi import Query
from typing import Optional
from enum import Enum

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

class Filter:
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        self.name = name
        self.description = description



def add_fields(**kwargs):
    def decorator(cls):
        for name, value in kwargs.items():
            setattr(cls, name, value)
        return cls
    return decorator

def add_filter_params(filter_params):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for param in filter_params:
                if param not in kwargs:
                    kwargs[param] = Query(None)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@add_filter_params(["name"])
class ItemFilter(Filter):
    pass