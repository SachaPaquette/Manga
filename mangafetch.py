# Description: This script fetches manga info from mangadex.org and inserts it into a MongoDB database.
from Config.config import Config
from Config.logs_config import setup_logging
from MangaFetch.FetchOperations import main

# Set up logging to a file
logger = setup_logging('manga_fetch', Config.MANGA_FETCH_LOG_PATH)

if __name__ == '__main__':
    # Run the main function in FetchOperations.py
    main()
