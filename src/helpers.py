import datetime

def before_equal_to_today(date: datetime.datetime):
    """
    Returns True if the given date is before or equal to today.
    """
    return date <= datetime.datetime.now()

def before_equal_to_today(date: datetime.date):
    """
    Returns True if the given date is before or equal to today.
    """
    return date <= datetime.date.today()