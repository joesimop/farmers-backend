
#Generates the parameter binds for a SQL query and the ILIKE search clauses.
def build_search_statements(fieldDict):
    search_clauses = []
    binds = {}
    for key, value in fieldDict.items():
        if value:
            search_clauses.append(f"{key} ILIKE :{key} ")
            binds[key] = f"%{value}%"

    #Return a dict of field names and their corresponding search clauses.
    return binds, search_clauses

def expand_search_statements(search_clauses, join_with_and = False):
    #Expand the search clauses into a string that can be used in a SQL query.

    #If no search clauses were provided, return an empty string.
    if search_clauses == []:
        return ""
    
    search_join = "AND " if join_with_and  else "OR "

    search_string = "AND ("
    for search in search_clauses:
        search_string += f"{search} {search_join}"

    #Remove the trailing " OR" from the search string and add a closing parenthesis.
    return (search_string[:-5] if join_with_and else search_string[:-4] ) + ")"
