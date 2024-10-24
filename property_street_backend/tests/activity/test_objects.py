# Test data
feature_obj = {
    0: {
        "db_table_id": 1,
        "db_table_name": "Agent",
    },
    1: {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value1"
        }
    },
    2: {
        # tag 2
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value2"
        }
    },
    3: {
        # cover image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkf",
            "format": "jpg",
            "bytes": 102400,
            "height": 800,
            "public_id": "test_image_123",
            "secure_url": "https://example.com/test_image.jpg",
            "width": 600,
        }
    },
    4: {
        # Asset
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Asset",

        # fields
        "fields": {
            "title": "value",
            "country": "Caicos",
            "address": "Barbados street",
            "currency": "usd",
            "status": "Auction",
            "amount": 30000.98,
            "category": "House",
            "status": "auction",
            "description": "<span>bla bla bla</span>",
            "has_features": True,

            "relationship": {
                "tags": [1, 2],
                "cover_image": 3,
                "agent": 0,
            }
        },
    },
    5: {
        # image for asset feature
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",

        # fields
        "fields": {
            "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
            "format": "jpg",
            "bytes": 102400,
            "height": 800,
            "public_id": "test_image_123",
            "secure_url": "https://example.com/test_image.jpg",
            "width": 600,
        }
    },
    6: {
        # asset features
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetFeature",

        # fields
        "fields": {
            "title": "value",

            "relationship": {
                "cloud_images": [5],
                "asset": 4,
            }
        },

    },
}

no_feature_obj = {
    0: {
        "db_table_id": 1,
        "db_table_name": "Agent",
    },
    1: {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value"
        }
    },
    2: {
        # cover image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkf",
            "format": "jpg",
            "bytes": 102400,
            "height": 800,
            "public_id": "test_image_123",
            "secure_url": "https://example.com/test_image.jpg",
            "width": 600,
        }
    },
    3: {
        # asset feature image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",

        # fields
        "fields": {
            "cloud_asset_id":"dajdlkajdlkajsdkfjasldkfj",
            "format": "jpg",
            "bytes": 102400,
            "height": 800,
            "public_id": "test_image_1",
            "secure_url": "https://example.com/test_image.jpg",
            "width": 600,
        },
    },
    4: {
        # asset feature image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",

        # fields
        "fields": {
            "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
            "format": "jpg",
            "bytes": 102400,
            "height": 800,
            "public_id": "test_image_2",
            "secure_url": "https://example.com/test_image.jpg",
            "width": 600,
        },
    },
    5: {
        # asset feature image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",

        # fields
        "fields": {
            "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
            "format": "jpg",
            "bytes": 102400,
            "height": 800,
            "public_id": "test_image_3",
            "secure_url": "https://example.com/test_image.jpg",
            "width": 600,
        },
    },
    6: {
        # Asset
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Asset",

        # fields
        "fields": {
            "title": "value",
            "country": "Caicos",
            "address": "Barbados street",
            "currency": "usd",
            "status": "Auction",
            "amount": 30000.98,
            "category": "House",
            "status": "auction",
            "description": "<span>bla bla bla</span>",
            "has_features": False,
        },

        "relationship": {
            "tags": [1],
            "cover_image": 2,
            "cloud_images":[3,4,5]
        }
    },
}

update_obj = {
}