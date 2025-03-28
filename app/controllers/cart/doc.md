# Cart documentation
<!--This implementation is programmed to reduce database writes by utilizing redis for cache functionalities, and celery for periodic offload to the database-->

## set keys 
- cart_pre_offload_{user_id}
- cart_pre_deletion_{user_id}
- cart_{user_id}

## set storage format
- The redis cache should store assets in the format
```json
{
  "asset_id": {
    "quantity": int,
    "asset_cover_url": url,
    "asset_title": string,
    "price": float
  },
  ...
}
```



## get_cart functionality logic
- The user's cart_pre_offload set should be first looked up for, any data found should be added to the result
- Then the user's cart entry should be search for
    - If contents are present, it's also added to the result object
    - else, the database should be searched. If the database contains cart items, it should be cached to cart_pre_offload, the ttl reset, and added to the result object.

## add_to_cart functionality logic
- Check the cart_pre_deletion set; if the asset is set for deletion off the user's record, but not actually deleted.
    - If it is, it's moved to the cart set, and the ttl updated and the function is returned.
- The `cart` set is checked
    - If the asset_id to add does not exist, add the asset and update the expiry.
    - return the function.
- When none of the above cases returns true, (the asset_id is not found under the user's cart-items or the user has n no cart storage), the `cart_pre_offload` hset is then checked for the asset_id.
        - If not found, the cart-item is added to the `cart_pre_offload` hset (which would later be offloaded to the database).

## remove_from_cart functionality logic
- The cart_pre_offload set is first checked. 
    - If the asset_id exist, it's removed and the function is returned.
    - Else the cart set is checked. 
        - If it's present in the cart set, the data is removed, the ttl updated, then the item is added to the cart_pre_delete set(then later offloaded).

## clear cart
- All cart_pre_offload asset_id is added to the cart_pre_deletion set, then deleted
- All cart items is added to the cart_pre_deletion set, deleted

## offload mechanism
At offload_time, a cron-job is ran to move all items from cart_pre_offload to the database, and then to the cart.
    On addition of an entry to the cart set, a ttl is set 