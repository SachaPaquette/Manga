# Description: This script fetches manga info from mangadex.org and inserts it into a MongoDB database.
import re
import time
from database import insert_manga_to_db, detect_duplicates, remove_doujinshi
from tqdm import tqdm  # Import tqdm for the progress bar
import random
from Config.config import Config
from Config.logs_config import setup_logging
from Driver.driver_config import driver_setup
from MangaFetch.FetchOperations import process_manga_pages, get_user_confirmation,main
# Set up logging to a file
logger = setup_logging('manga_fetch', Config.MANGA_FETCH_LOG_PATH)





"""
def main():
    try:
        update_symbols = get_user_confirmation(
            "Do you want to add manga names to the database? (Y/n): ", default="y")  # Get user confirmation

        if update_symbols != "n":
            driver = driver_setup()  # Setup the driver
            process_manga_pages(driver)  # Process the manga pages
        else:
            print("No mangas will be added to the database.")
            return

        detect_duplicates()  # Detect and remove duplicate documents
        remove_doujinshi()  # Remove doujinshi from the database (fan-made manga)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Quitting...")
    finally:
        if 'driver' in locals():
            driver.quit()  # Quit the driver"""


if __name__ == '__main__':
    main()
