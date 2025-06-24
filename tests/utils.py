import time

def get_user_ws_endpoint(access_token,**kwargs):
    timestamp = kwargs.get('timestamp',int(time.time()*1000))
    last_n_timestamp = kwargs.get('last_n_timestamp',None)
    return  (
        f'ws://localhost:8001/ws?sesion_ts={timestamp}&access_token={access_token}&last_n_timestamp={last_n_timestamp}'
        if last_n_timestamp else
        f'ws://localhost:8001/ws?sesion_ts={timestamp}&access_token={access_token}' 
    )
