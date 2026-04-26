def is_safe_sql(query: str) -> bool:
    forbidden_words = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
    query_upper = query.upper()
    if any(word in query_upper for word in forbidden_words):
        return False
    return True