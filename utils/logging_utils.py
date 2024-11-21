import logging

def setup_logging():

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vetsai.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    return logger
