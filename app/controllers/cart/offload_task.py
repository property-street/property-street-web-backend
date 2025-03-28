import json
from sqlalchemy.sql import insert
from property_street_backend.log_config.logger_config import log_message


from .models import CartItem
from property_street_backend.app.database import get_db

async def handle_cart_offload(
    cart_ttl,
    redis_client,
):
    try:
        cursor = b"0"
        cart_data = {} # # { int:user_id -> { asset_id -> {quantity, asset_cover_url, asset_title, price} } }
        bulk_records = []
        keys_to_delete = set()  # Collect keys for bulk deletion


        # Fetch all keys matching cart pattern
        # map each cart_items to the user_id in the cart_data hash map
        while cursor:
            cursor, keys = await redis_client.scan(cursor, match="cart_pre_offload_*", count=1000)
            
            if not keys:
                break  # No more keys to process

            for key in keys:
                user_id = int(key.decode().split("_")[-1])  # Extract user ID from key
                cart_data[user_id] = await redis_client.get(key)  # Get the cart string
            
            keys_to_delete.update(keys)  # Store keys for deletion

        # loop over the cart_data
        # load the cart_items
        for user_id, cart_object_str in cart_data.items():
            loaded_cart_object = json.loads(cart_object_str)
            
            # loop over the loaded cart items
            # Make a cart item instance and add to bulk records
            for asset_id, cart_details in loaded_cart_object.items():
                cart_item = {
                    "asset_id": int(asset_id),
                    "quantity": cart_details.quantity,
                    "user_id": user_id
                }
                bulk_records.append(cart_item)
            
            # store the cart object string to the user_cart with expiry
            cart_key = f'cart_{user_id}'
            await redis_client.set(cart_key, cart_object_str, ex=cart_ttl)

        if bulk_records:
            db = get_db().__anext__()
            stmt = insert(CartItem).values(bulk_records)
            await db.execute(stmt)  # Bulk insert
            await db.commit()

            # Bulk delete only after DB save is successful
            if keys_to_delete:
                await redis_client.unlink(*keys_to_delete)  # Non-blocking deletion

        # log the success
        log_message(
            'success',
            f'Successful offload of cart_pre_offload sets to the database.'
        )
    except Exception as e:
        # log the success
        log_message(
            'error',
            f'Error offloading cart_pre_offload sets to the database. Reason: {e}'
        )