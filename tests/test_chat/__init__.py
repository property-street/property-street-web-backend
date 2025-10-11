sender = {
    "id": 1,
    "username": "john",
    "user_role": "user",
    "avatar": { "url": "..." }
}
recipient = {
    "id": 2,
    "username": "jane",
    "user_role": "user",
    "avatar": { "url": "..." }
}

fmt_msg = {
    "text_content": "Hello!",
    "media_urls": ["https://cdn.domain.com/file1.jpg", "https://cdn.domain.com/file2.png"],
    "sender": sender,
    "recipient": recipient,
    "reactions": {
        "👍": ["user1", "user2"],
        "❤️": ["user3"]
    },
    "additional_metadata": {
        "edited": False,
        "pinned": False
    }
}

message = {
    "category": "chat",
    "msg_type": "outbound_message",
    "fmt_msg": fmt_msg,
    'status': 'unsent',
    'sender': sender,
    'recipient': recipient,
}