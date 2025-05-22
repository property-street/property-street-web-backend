import time

def get_user_ws_endpoint(access_token):
    timestamp = int(time.time()*1000)
    return  f'ws://localhost:8001/ws?sesion_ts={timestamp}&access_token={access_token}'
