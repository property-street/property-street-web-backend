cloud_image_template = {
    "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
    "format":"jpg",
    "bytes":102400,
    "height":800,
    "public_id":"test_image_123",
    "secure_url":"https://example.com/test_image.jpg",
    "width":600,
}
area_template = {
    'country':'Sri-lanka',
    'state_or_province': 'Mogadishu',
    'city_or_town': 'Pisque Central', 
    'street': 'No 11 Jokey street',
    "zip_or_postal_code": "",
	"building_name_or_suite": "",
}
asset_data_template = {        
    "title":"Test Asset",
    "currency":"USD",
    "price":100000.00,
    "description":"Test description",
    "category":"House",
    "status":"auction",
    "availability":"available",
}
tags_template = ["house", "condo"]

# Test data
feature_obj = {
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
            **cloud_image_template,
            "public_id": "test_image_123",
        }
    },
    4: {
        # Asset
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Asset",

        # fields
        "fields": {
            **asset_data_template,

            "relationship": {
                "tags": [1, 2],
                "cover_image": 3,
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
    7: {
        # Area
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Area",

        # fields
        "fields": {
            **area_template,

            # relationships
            "relationship":{
                "asset": 4
            }
        }
    },
    8: {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value1",

            "relationship":{
                "asset": 4,
            }
        }
    },
}

no_feature_obj1 = {
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
            **asset_data_template,

            "relationship": {
                "tags": [1],
                "cover_image": 2,
                "cloud_images":[3,4,5]
            }
        },
    },
    7: {
        # Area
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Area",

        # fields
        "fields": {
            **area_template,

            # relationships
            "relationship":{
                "asset": 6
            }
        }
    },
    8: {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value1",

            "relationship":{
                "asset": 6,
            }
        }
    },
}

no_feature_obj = {
    "1": {
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Asset",
        
        "fields": {
            "title":"Guadalajara Studio",
            "currency":"MXN",
            "price":350000,
            "description":"Modern studio apartment with excellent lighting and near coworking spaces.",
            "category":"Studio",
            "status":"lease",
            "lease_duration": "6 months",
        }
    },
    "2": {
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",
        "fields": {
            "name": "Studio",
            
            "relationship": {
                "asset": 1
            }
        },
    },
    "3": {
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",
        "fields": {
            "name": "Mexico",

            "relationship": {
                "asset": 1
            }
        },
    },
    "4": {
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "CloudImageDetail",
        "fields": {
            "cloud_asset_id": "a27193f48caaa82d1755d2fb86d0f9a0",
            "format": "png",
            "bytes": 645381,
            "height": 1058,
            "public_id": "gzzcyl2egmmopyyqfui4",
            "secure_url": "https://res.cloudinary.com/dmjtks9zq/image/upload/v1752509909/gzzcyl2egmmopyyqfui4.png",
            "width": 665,

            "relationship": {
                "asset": 1
            }
        },
    },
    "5": {
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",
        "fields": {
            "cloud_asset_id": "dbb422312d74b5323477fd30c1f656c5",
            "format": "png",
            "bytes": 1083289,
            "height": 780,
            "public_id": "xuasi3vhdircto6rv7sm",
            "secure_url": "https://res.cloudinary.com/dmjtks9zq/image/upload/v1752509953/xuasi3vhdircto6rv7sm.png",
            "width": 1170,
            
            "relationship": {
                "asset": 1
            }
        }
    },
    "6": {
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",
        "fields": {
            "cloud_asset_id": "ef0e01dacc3bee938b4c2cd2de9f0d4c",
            "format": "png",
            "bytes": 781062,
            "height": 780,
            "public_id": "guvtnlmp39m6ex4k7uq4",
            "secure_url": "https://res.cloudinary.com/dmjtks9zq/image/upload/v1752510001/guvtnlmp39m6ex4k7uq4.png",
            "width": 1170,

            "relationship": {
                "asset": 1
            }
        }
    },
    "7": {
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetCloudImage",
        "fields": {
            "cloud_asset_id": "6e469d2771de12d067c3021c87d36a4d",
            "format": "jpg",
            "bytes": 1073006,
            "height": 1856,
            "public_id": "shpnxczlklgjgifscjs1",
            "secure_url": "https://res.cloudinary.com/dmjtks9zq/image/upload/v1752510059/shpnxczlklgjgifscjs1.jpg",
            "width": 2784,

            "relationship": {
                "asset": 1
            }
        }
    },
    "8": {
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Area",

        "fields": {
            "country": "Mexico",
            "state_or_province": "Jalisco",
            "city_or_town": "Guadalajara",
            "street": "102 Avenida Chapultepec",

            "relationship":{
                "asset": 1
            }
        }
    },
}

agent_assets = {
    0:{
        'category': str,
        'cover_image':{
            'db_table_id': int,
            'cloud_details':dict,
        },
        'country': str,
        'address': str,
        'currency': str,
        'amount': float,
        'status': str,
        'tags':[
            {
                'db_table_id': int,
                'name': str
            },
            # ...
        ],
        'feature':{
            0:{
                'title':str,
                'db_table_id': int,
                'cloud_images':{
                    'public_id':dict, # dictionary of the cloud image details with the entries including database table id
                    # ...
                }
            }
            # ...
        },
        # or
        'no_feature':{
            0:{
                'cloud_detais':{
                    'public_id':dict, # dictionary of the cloud image details with the entries including the database table id
                    # ...
                }
            }
        }
    }
}