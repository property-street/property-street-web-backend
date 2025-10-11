import logging
import os

# Directory for log files
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Function to get or create a logger based on the log type
def get_logger(log_type):
    log_file = os.path.join(log_dir, f"{log_type}.log")
    
    # Check if the logger already exists
    if log_type in logging.Logger.manager.loggerDict:
        return logging.getLogger(log_type)
    
    # Create a new logger if not found
    logger = logging.getLogger(log_type)
    if log_type == "error":
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)  # For "success" or other types
    
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Function to log messages based on the log type
def log_message(log_type, message):
    logger = get_logger(log_type)
    logger.info(message) if log_type != "error" else logger.error(message)
    truncate_log_file(logger.handlers[0].baseFilename)

def log_error(message):
    log_message('error',message)

def log_success(message):
    log_message('success',message)

# Function to truncate log files to 100 lines
def truncate_log_file(file_path, max_lines=100):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        if len(lines) > max_lines:
            with open(file_path, 'w') as file:
                file.writelines(lines[-max_lines:])
    except Exception as e:
        # Log the error using the log_message function but prevent recursion
        error_logger = get_logger("error")
        error_logger.error(f"Truncation error: {e}")
