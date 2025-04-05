import json
import redis.asyncio as redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.controllers.cart.models import CartItem
from .schemas import AddToCartSchema

class CartService:
    @staticmethod
    async def get_cart(
        user_id: int, 
        cart_ttl: int,
        db:AsyncSession, 
        redis_client:redis.Redis,
    ):
        """Retrieve the cart from Redis"""
        result = {}
        cart_key = f"cart_{user_id}"
        cart_pre_offload_key = f"cart_pre_offload_{user_id}"
        
        # check on the cart_pre_offload hset
        client_cart_pre_offload_data = await redis_client.get(cart_pre_offload_key)
        if client_cart_pre_offload_data:
            result.update(json.loads(client_cart_pre_offload_data))

        # check on the cart set
        client_cart_set = await redis_client.get(cart_key)
        if client_cart_set:
            result.update(json.loads(client_cart_set))
        
        if not result:
            query = await db.execute(
                select(CartItem).filter(CartItem.user_id == user_id)
            )
            cart_list = query.scalars().all()  # Fetch all cart items
            cart_list_dic_exp = {
                cart_item.asset_id : {
                    "quantity": cart_item.quantity,
                    "asset_cover_url": cart_item.asset.cover_image.secure_url,
                    "asset_title": cart_item.asset.title,
                    "price": float(cart_item.asset.price),
                } 
                for cart_item in cart_list
            }

            # extend the result, and update the cache if a result is returned
            if cart_list_dic_exp:
                result.update(cart_list_dic_exp)
                await redis_client.set(cart_key, json.dumps(cart_list_dic_exp), ex=cart_ttl)
        
        return result

    @staticmethod
    async def add_to_cart(
        user_id: int, 
        asset_id: int, 
        cart_ttl: int,
        redis_client: redis.Redis,
        cart_item_details: dict,
        # cart_item_details: AddToCartSchema,
    ):
        """Adds an item to the cart"""
        cart_key = f'cart_{user_id}'
        cart_pre_offload_key = f'cart_pre_offload_{user_id}'
        cart_pre_deletion_key = f'cart_pre_deletion_{user_id}'
        asset_id_to_str = str(asset_id)
        # cart_item_details_to_dict = vars(cart_item_details)

        # get user cart items
        user_cart_items = await redis_client.get(cart_key)
        loaded_user_cart_items = json.loads(user_cart_items) if user_cart_items else {}

        # check for a cart_pre_deletion set of the user,
        # and then look for the entry
        user_pre_deletion_items = await redis_client.get(cart_pre_deletion_key)
        loaded_deletion_data = json.loads(user_pre_deletion_items) if user_pre_deletion_items else {}
        if loaded_deletion_data.get(asset_id_to_str):
            loaded_deletion_data.pop(asset_id_to_str)
            
            # update the deletion_cart
            if loaded_deletion_data:
                await redis_client.set(cart_pre_deletion_key, json.dumps(loaded_deletion_data))
            else:
                await redis_client.delete(cart_pre_deletion_key)

            # update the cart
            loaded_user_cart_items[asset_id] = cart_item_details
            await redis_client.set(cart_key, json.dumps(loaded_user_cart_items), ex=cart_ttl)
            return

        # check in the cart set and 
        # return the function if it exists for the specified user_id
        if user_cart_items and not loaded_user_cart_items.get(asset_id_to_str):
            loaded_user_cart_items[asset_id] = cart_item_details
            await redis_client.set(cart_key, json.dumps(loaded_user_cart_items), ex=cart_ttl)
            return

        # check if the asset exists in the user_pre_offload hset
        user_cart_pre_offload_items = await redis_client.get(cart_pre_offload_key) 
        loaded_pre_offload_data = json.loads(user_cart_pre_offload_items) if user_cart_pre_offload_items else {}
        # if the asset does not exist
        if not loaded_pre_offload_data.get(asset_id_to_str):
            loaded_pre_offload_data[asset_id] = cart_item_details
            await redis_client.set(cart_pre_offload_key, json.dumps(loaded_pre_offload_data))
        
    @staticmethod
    async def remove_from_cart(
        user_id: int, 
        asset_id: int,
        cart_ttl: int,
        redis_client: redis.Redis,
    ):
        """Remove an item from the cart"""
        cart_key = f'cart_{user_id}'
        cart_pre_offload_key = f'cart_pre_offload_{user_id}'
        cart_pre_deletion_key = f'cart_pre_deletion_{user_id}'
        asset_id_to_str = str(asset_id)
        
        # user's cart pre-offload data
        user_pre_offload_data = await redis_client.get(cart_pre_offload_key)
        loaded_user_pre_offload_data = json.loads(user_pre_offload_data) if user_pre_offload_data else {}
        # check that the data exists
        if loaded_user_pre_offload_data.get(asset_id_to_str):
            loaded_user_pre_offload_data.pop(asset_id_to_str)
            # update the hset if object is non empty, else delete the hset entry
            if loaded_user_pre_offload_data:
                await redis_client.set(cart_pre_offload_key, json.dumps(loaded_user_pre_offload_data))
            else:
                await redis_client.delete(cart_pre_offload_key)
            return

        # check the cart set
        user_cart_data = await redis_client.get(cart_key)
        loaded_user_cart_data = json.loads(user_cart_data) if user_cart_data else {}
        # check if the data exists in the cart hset
        if loaded_user_cart_data.get(asset_id_to_str):
            # remove the data from the set, store the object
            removed_object = loaded_user_cart_data.pop(asset_id_to_str)
            
            # update the user's entry or delete the entry depending on the case
            if loaded_user_cart_data:
                await redis_client.set(cart_key, json.dumps(loaded_user_cart_data), ex=cart_ttl)
            else:
                await redis_client.delete(cart_key)

            # add the data to the cart_pre_deletion set
            pre_deletion_data = await redis_client.get(cart_pre_deletion_key)
            loaded_pre_deletion_data = json.loads(pre_deletion_data) if pre_deletion_data else {}
            loaded_pre_deletion_data[asset_id] = removed_object
            await redis_client.set(cart_pre_deletion_key, json.dumps(loaded_pre_deletion_data))

    @staticmethod
    async def clear_cart(
        user_id: int,
        redis_client: redis.Redis,
    ):
        cart_key = f'cart_{user_id}'
        cart_pre_offload_key = f'cart_pre_offload_{user_id}'
        cart_pre_deletion_key = f'cart_pre_deletion_{user_id}'

        # check the cart_pre_offload set for data
        cart_pre_offload_data = await redis_client.get(cart_pre_offload_key)
        loaded_cart_pre_offload_data = json.loads(cart_pre_offload_data) if cart_pre_offload_data else {}

        # check the cart set for data
        cart_data = await redis_client.get(cart_key)
        loaded_cart_data = json.loads(cart_data) if cart_data else {}

        joint_deletion_data = {}

        # add loaded_cart_pre_offload_data to joint_deletion_data
        if loaded_cart_pre_offload_data:
            joint_deletion_data.update(loaded_cart_pre_offload_data)
            await redis_client.delete(cart_pre_offload_key)
        # add loaded_cart_data to joint_deletion_data
        if loaded_cart_data:
            joint_deletion_data.update(loaded_cart_data)
            await redis_client.delete(cart_key)
            
        if joint_deletion_data:
            # check the cart set for data
            cart_pre_deletion_data = await redis_client.get(cart_pre_deletion_key)
            loaded_pre_deletion_data = json.loads(cart_pre_deletion_data) if cart_pre_deletion_data else {}
            loaded_pre_deletion_data.update(joint_deletion_data)

            await redis_client.set(cart_pre_deletion_key,json.dumps(loaded_pre_deletion_data))