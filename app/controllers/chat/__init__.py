def chat_dialogue_zset_key(sender_id:int, recipient_id:int, /)->str:
    """Accepts a sender and recipient id, and returns a zset key used to hold cached data for a dialogue chat.

    Args:
        sender_id (int): sender's user id
        recipient_id (int): recipient's user id

    Returns:
        str: zset key used to query redis cache.
    """
    return f'chat_{min(sender_id,recipient_id)}_{max(sender_id,recipient_id)}'