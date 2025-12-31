from .models_helper import (
    Area,
    AddOn,
    CloudImageDetail,
    GoogleOAuthDetail,
    EmailManagementModel,
    CloudDeletionOutbox,
)
from property_street_backend.app.controllers.chat.models import (
    Thread,
    ChatSession,
    Message,
) 
from property_street_backend.app.controllers.assets.models import (
    Tag,
    Asset,
    AssetFeature,
    AssetCloudImage,
) 
from property_street_backend.app.controllers.actors.models import (
    User
) 
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.app.controllers.ratings.models import Rating
from property_street_backend.app.controllers.settings.models import UserSetting
from property_street_backend.app.controllers.notification.models import Notification
from property_street_backend.app.controllers.asset_request.models import AssetRequest
from property_street_backend.app.controllers.roommate_finder.models import RoomieApplication, RoommateFinder




models = [
    Tag,
    User,
    Area,
    AddOn,
    Asset,
    Thread,
    Rating,
    Message,
    CartItem,
    ChatSession,
    UserSetting,
    AssetRequest,
    Notification,
    AssetFeature,
    RoommateFinder, 
    AssetCloudImage, 
    CloudImageDetail,
    GoogleOAuthDetail,
    RoomieApplication,
    CloudDeletionOutbox,
    EmailManagementModel,
]
