agent_pend_pool_key = "pend_pool_agent_notification"

def user_pend_pool_key(user_id:int,/)->str:
    """Accepts a user id and returns a proposed zset key 
    for holding data for a user on websocket failure.
        

    Args:
        user_id (int): id of a user

    Returns:
        str: a string used to query the redis cache for a specific user's data.
    """
    return f'pend_pool_{user_id}'