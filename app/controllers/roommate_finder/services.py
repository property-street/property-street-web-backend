from property_street_backend.app.controllers.actors.models import User

def get_cached_roomies_application_ids(requester: User)->list:
    return requester.cached_roomies_application_ids
