import logging
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from database import insert_manga_to_db, detect_duplicates, remove_doujinshi
from tqdm import tqdm  # Import tqdm for the progress bar
import random
from config import Config

def setup_logging():
    logging.basicConfig(filename='./Logs/MangaFetch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger(__name__)

def driver_setup():
    options = Options()
    options.add_experimental_option('detach', True)
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument("--log-level=3")
    options.add_argument(f"user-agent={random.choice(Config.USER_AGENTS)}") # Set a random user agent
    # ChromeDriverManager will install the latest version of ChromeDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_manga_cards(driver, page_number):
    manga_url = Config.MANGADEX_BASE_URL.format(page_number) # Format the URL with the page number
    driver.get(manga_url) # Navigate to the URL
    driver.implicitly_wait(random.uniform(2,3)) # Wait for the page to load
    manga_cards = driver.find_elements(by=By.CLASS_NAME, value='manga-card') # Find all the manga cards on the page
    return manga_cards # Return the list of manga cards

def extract_manga_info(manga_card):
    manga_link = manga_card.find_element(by=By.TAG_NAME, value='a').get_attribute('href') # Get the link to the manga
    manga_info = manga_card.text.split('\n') # Split the text into a list of strings
    manga_title = manga_info[0] # The first element in the list is the title
    manga_rating = next((element for element in manga_info if re.match(r'^\d+(\.\d+)?$', element) or element == 'N/A'), None) # Find the rating in the list

    if manga_rating:
        manga_status = manga_info[1] # The second element in the list is the status (ongoing, completed, etc.)
        manga_desc = manga_info[-1] # The last element in the list is the manga's description

        manga_dict = {
            'title': manga_title,
            'link': manga_link,
            'status': manga_status,
            'desc': manga_desc,
        }
        return manga_dict

    return None

def fetch_and_insert_mangas(driver, page_number):
    try:
        manga_array = [] # Create an empty array to store the manga info
        manga_cards = get_manga_cards(driver, page_number) # Get the manga cards on the page

        # Use tqdm to create a progress bar
        for manga_card in tqdm(manga_cards, desc=f"Processing page {page_number}", unit="manga"):
            
            manga_info = extract_manga_info(manga_card)
            if manga_info:
                manga_array.append(manga_info)

        insert_manga_to_db(manga_array) # Insert the manga info into the database

    except NoSuchElementException as e:
        logging.error(f"Error while fetching manga: {e}")
        print(f"No manga cards found on page {page_number}.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise

def get_user_confirmation(prompt):
    while True:
        user_input = input(prompt).lower() # Get user input and convert to lowercase
        if user_input in ["y", "n", ""]: # If the input is 'y', 'n' or empty
            return user_input # Return the input
        else:
            print("Invalid input. Please enter 'y' for yes or 'n' for no.")

def process_manga_pages(driver):
    sleep_threshold = random.randint(Config.MIN_SLEEP_THRESHOLD, Config.MAX_SLEEP_THRESHOLD) # Generate a random sleep threshold between min and max
    for page_number in range(1, Config.TOTAL_PAGES + 1):
        fetch_and_insert_mangas(driver, page_number)  # Fetch and insert the manga info into the database
        time.sleep(random.uniform(0.5, 2))  # Sleep for a random duration between 0.5 and 2 seconds
        if page_number % sleep_threshold == 0:  # If the page number is a multiple of the sleep threshold (sleep after every x pages)
            sleep_duration = random.uniform(Config.MIN_SLEEP_DURATION, Config.MAX_SLEEP_DURATION)  # Generate a random sleep duration between min and max
            for remaining_time in tqdm(range(int(sleep_duration)), desc=f"Sleeping for {int(sleep_duration)} seconds"):
                time.sleep(1)
            # Change sleep_threshold after it's first hit
            sleep_threshold = random.randint(Config.MIN_SLEEP_THRESHOLD, Config.MAX_SLEEP_THRESHOLD) # Generate a new random sleep threshold between min and max


def main():
    try:
        setup_logging() # Setup logging
        update_symbols = get_user_confirmation("Do you want to add manga names to the database? (Y/n): ") # Get user confirmation
        
        if update_symbols != "n": 
            driver = driver_setup() # Setup the driver
            process_manga_pages(driver) # Process the manga pages
        else:
            print("No mangas will be added to the database.")
            return
        
        detect_duplicates() # Detect and remove duplicate documents
        remove_doujinshi() # Remove doujinshi from the database (fan-made manga)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Quitting...")
    finally:
        if 'driver' in locals():
            driver.quit() # Quit the driver

if __name__ == '__main__':
    main()
