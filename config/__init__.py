import os

def get_env():
    # environment retrieval based on context
    TEST_ENV = os.getenv("TEST_ENV")
    env = 'test' if TEST_ENV else 'prod'
    return env

def env_is_test():
    # environment retrieval based on context
    return get_env() == 'test'