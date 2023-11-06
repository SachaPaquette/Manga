import re
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from database import insert_manga_to_db, detect_duplicates, remove_doujinshi
from tqdm import tqdm  # Import tqdm for the progress bar
import random
from Config.config import Config
from Config.logs_config import setup_logging
from Driver.driver_config import driver_setup
logger = setup_logging('manga_fetch', Config.MANGA_FETCH_LOG_PATH)


def format_manga_url(page_number):
    # Format the manga url with the page number
    return Config.MANGADEX_BASE_URL.format(page_number)


def navigate_to_manga_url(driver, manga_url):
    driver.get(manga_url)  # Navigate to the manga url


def wait_for_page_to_load(driver, min_wait=2, max_wait=3):
    # Wait for the page to load
    driver.implicitly_wait(random.uniform(min_wait, max_wait))


def find_manga_cards(driver):
    # Find the manga cards on the page
    return driver.find_elements(by=By.CLASS_NAME, value='manga-card')


def fetch_manga_cards(driver, page_number):
    manga_url = format_manga_url(page_number)  # Format the manga url
    navigate_to_manga_url(driver, manga_url)  # Navigate to the manga url
    wait_for_page_to_load(driver)  # Wait for the page to load
    manga_cards = find_manga_cards(driver)  # Find the manga cards on the page
    return manga_cards  # Return the manga cards


def get_manga_link(manga_card):
    # Get the manga link
    return manga_card.find_element(by=By.TAG_NAME, value=Config.HYPERLINK).get_attribute(Config.HREF)


def get_manga_info_list(manga_card):
    # Split the manga card text by newline characters
    return manga_card.text.split('\n')


def get_manga_title(manga_info_list):
    # Return the first element in the manga info list, the title
    return manga_info_list[0]


def get_manga_rating(manga_info_list):
    # Return the first element in the manga info list that matches the regex or is 'N/A'
    return next((element for element in manga_info_list if re.match(r'^\d+(\.\d+)?$', element) or element == 'N/A'), None)


def get_manga_status(manga_info_list):
    # Return the second element in the manga info list, the status (ex: Ongoing, Completed)
    return manga_info_list[1] if len(manga_info_list) > 1 else None


def get_manga_description(manga_info_list):
    # Return the last element in the manga info list, the description
    return manga_info_list[-1] if manga_info_list else None


def create_manga_dict(title, link, status, desc):
    return {
        'title': title,
        'link': link,
        'status': status,
        'desc': desc,
    }  # Return a dictionary with the manga info


def extract_manga_info(manga_card):
    manga_link = get_manga_link(manga_card)  # Get the manga link
    manga_info_list = get_manga_info_list(
        manga_card)  # Get the manga info list
    if manga_info_list:
        manga_title = get_manga_title(manga_info_list)  # Get the manga title
        manga_rating = get_manga_rating(
            manga_info_list)  # Get the manga rating
        manga_status = get_manga_status(
            manga_info_list)  # Get the manga status
        manga_desc = get_manga_description(
            manga_info_list)  # Get the manga description

        if manga_rating:
            # Return the manga info if the manga rating is not None
            return create_manga_dict(manga_title, manga_link, manga_status, manga_desc)
        return None


def fetch_and_process_manga_cards(driver, page_number):
    manga_cards = fetch_manga_cards(driver, page_number)
    manga_array = []

    # Create a progress bar for the manga cards
    for manga_card in tqdm(manga_cards, desc=f"Processing page {page_number}", unit="manga"):
        manga_info = extract_manga_info(manga_card)  # Extract the manga info
        if manga_info:  # Check if the manga info is not None
            # Append the manga info to the manga array
            manga_array.append(manga_info)

    return manga_array  # Return the manga array


def handle_no_such_element_exception(logger, page_number, exception):
    logger.error(f"Error while fetching manga: {exception}")
    # Print an error message
    print(f"No manga cards found on page {page_number}.")


def handle_unexpected_exception(logger, exception):
    logger.error(f"An unexpected error occurred: {exception}")
    raise


def process_and_insert_mangas(driver, page_number):
    try:
        manga_array = []  # Create an empty manga array
        # Fetch and process the manga cards
        manga_array += fetch_and_process_manga_cards(driver, page_number)
        # Insert the manga array into the database
        insert_manga_to_db(manga_array)

    except NoSuchElementException as e:
        # Handle no such element exception
        handle_no_such_element_exception(logger, page_number, e)

    except Exception as e:
        handle_unexpected_exception(logger, e)  # Handle unexpected exceptions


def get_user_confirmation(prompt, default="y"):
    while True:
        # Get user input and convert to lowercase
        user_input = input(f"{prompt} ").lower()
        if user_input in ["y", "n", ""]:  # If the input is 'y', 'n' or empty
            return user_input or default  # Return the input
        else:
            print("Invalid input. Please enter 'y' for yes or 'n' for no.")


def generate_random_sleep_threshold(min_threshold, max_threshold):
    # Generate a random integer between the min and max thresholds
    return random.randint(min_threshold, max_threshold)


def fetch_and_insert_mangas_with_sleep(driver, page_number, sleep_threshold):
    process_and_insert_mangas(driver, page_number)  # Fetch and insert mangas
    # Sleep for a random duration between 0.5 and 2 seconds
    time.sleep(random.uniform(0.5, 2))

    if page_number % sleep_threshold == 0:  # Check if the page number is a multiple of the sleep threshold
        sleep_duration = random.uniform(
            Config.MIN_SLEEP_DURATION, Config.MAX_SLEEP_DURATION)  # Generate a random sleep duration
        # Sleep for the specified duration
        sleep_for_duration_with_progress(sleep_duration)


def sleep_for_duration_with_progress(duration):
    # Create a progress bar for the sleep duration and iterate over the range
    for remaining_time in tqdm(range(int(duration)), desc=f"Sleeping for {int(duration)} seconds"):
        time.sleep(1)


def update_sleep_threshold(page_number, current_threshold):
    if page_number % current_threshold == 0:  # Check if the page number is a multiple of the current threshold
        return generate_random_sleep_threshold(
            Config.MIN_SLEEP_THRESHOLD, Config.MAX_SLEEP_THRESHOLD)  # Generate a new sleep threshold if the page number is a multiple of the current threshold
    # Return the current threshold if the page number is not a multiple of the current threshold
    return current_threshold


def process_manga(driver):
    sleep_threshold = generate_random_sleep_threshold(
        Config.MIN_SLEEP_THRESHOLD, Config.MAX_SLEEP_THRESHOLD)  # Generate a random sleep threshold
    for page_number in range(1, Config.TOTAL_PAGES + 1):
        fetch_and_insert_mangas_with_sleep(
            driver, page_number, sleep_threshold)  # Fetch and insert mangas
        sleep_threshold = update_sleep_threshold(
            page_number, sleep_threshold)  # Update the sleep threshold


def handle_user_confirmation():
    return get_user_confirmation(
        "Do you want to add manga names to the database? (Y/n): ", default="y")  # Get user confirmation and return the input


def setup_driver_if_needed(update_symbols):
    # Set up the driver if the user wants to update the database
    return driver_setup() if update_symbols != "n" else None


def perform_main_workflow(driver):
    if driver:  # Check if the driver is initialized
        process_manga(driver)  # Process the manga pages
        detect_duplicates()  # Detect and remove duplicates
        remove_doujinshi()  # Remove doujinshi from the database (fan-made manga)


def cleanup(driver):
    if driver:
        driver.quit()  # Close the browser window


def main():
    driver = None  # Initialize the driver variable
    try:
        update_symbols = handle_user_confirmation()  # Get user confirmation
        # Set up the driver if needed
        driver = setup_driver_if_needed(update_symbols)
        # Perform the main workflow (fetching and inserting mangas)
        perform_main_workflow(driver)

    except Exception as e:
        handle_unexpected_exception(logger, e)  # Handle unexpected exceptions
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Quitting...")
    finally:
        cleanup(driver)
