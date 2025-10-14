from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template

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
    "media": [{**cloud_image_template}],
    "reactions": {
        "👍": [sender, recipient],
        "❤️": [recipient]
    },
    "additional_metadata": {
        "edited": False,
        "pinned": False
    },
    "ui_inbound_timestamp_ms": 0,
    "ui_outbound_timestamp_ms": 0
}

message = {
    "category": "chat",
    "msg_type": "outbound_message",
    "fmt_msg": fmt_msg,
    'status': 'unsent',
    'sender': sender,
    'recipient': recipient,
}