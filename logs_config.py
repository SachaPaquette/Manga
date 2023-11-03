import logging

def setup_logging(logger_name, log_file):
    logger = logging.getLogger(logger_name) # Create a logger
    logger.setLevel(logging.INFO) # Set the log level to INFO of the logger
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') # Format the log messages
    
    file_handler = logging.FileHandler(log_file) # Log to a file
    file_handler.setLevel(logging.INFO) # Set the log level to INFO of the file handler
    file_handler.setFormatter(formatter) # Set the formatter for the file handler
    
    logger.addHandler(file_handler) # Add the file handler to the logger

    return logger