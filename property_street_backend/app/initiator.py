from fastapi import FastAPI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)\
#logging.basicConfig(level=logging.DEBUG)  # Set the logging level to DEBUG or lower as needed


app = FastAPI()

