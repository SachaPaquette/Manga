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


def format_manga_url(manga_name):
    """
    Formats the manga url with the given page number.

    Args:
        page_number (int): The page number to format the url with.

    Returns:
        str: The formatted manga url.
    """
    # Format the manga url with the page number
    return Config.MANGADEX_SEARCH_URL.format(manga_name)


def navigate_to_manga_url(driver, manga_url):
    """
    Navigates the driver to the specified manga URL.
    
    Args:
        driver: The Selenium WebDriver instance to use for navigation.
        manga_url: The URL of the manga to navigate to.
    """
    driver.get(manga_url)  # Navigate to the manga url


def wait_for_page_to_load(driver, min_wait=2, max_wait=3):
    """
    Wait for the page to load using implicit wait.

    Args:
        driver: The webdriver instance.
        min_wait (float): The minimum wait time in seconds.
        max_wait (float): The maximum wait time in seconds.

    Returns:
        None
    """
    driver.implicitly_wait(random.uniform(min_wait, max_wait))


def find_manga_cards(driver):
    """
    Finds all the manga cards on the page.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of WebElements representing the manga cards.
    """
    return driver.find_elements(by=By.CLASS_NAME, value='manga-card')


def fetch_manga_cards(driver, manga_name):
    """
    Fetches manga cards from a given page number.

    Args:
        driver: The Selenium WebDriver instance.
        page_number (int): The page number to fetch manga cards from.

    Returns:
        A list of manga cards found on the page.
    """
    manga_url = format_manga_url(manga_name)  # Format the manga url
    navigate_to_manga_url(driver, manga_url)  # Navigate to the manga url
    wait_for_page_to_load(driver)  # Wait for the page to load
    manga_cards = find_manga_cards(driver)  # Find the manga cards on the page
    return manga_cards  # Return the manga cards


def get_manga_link(manga_card):
    """
    Get the hyperlink of the manga from the given manga card element.

    Args:
        manga_card (WebElement): The manga card element.

    Returns:
        str: The hyperlink of the manga.
    """
    return manga_card.find_element(by=By.TAG_NAME, value=Config.HYPERLINK).get_attribute(Config.HREF)


def get_manga_info_list(manga_card):
    """
    Splits the manga card text by newline characters and returns a list of strings.

    Args:
        manga_card (WebElement): The manga card element.

    Returns:
        list: A list of strings containing the manga information.
    """
    return manga_card.text.split('\n')


def get_manga_title(manga_info_list):
    """
    Returns the title of a manga from the given manga info list.

    Args:
    manga_info_list (list): A list containing information about a manga, with the title as the first element.

    Returns:
    str: The title of the manga.
    """
    # Return the first element in the manga info list, the title
    return manga_info_list[0]


def get_manga_rating(manga_info_list):
    """
    Returns the first element in the manga info list that matches the regex pattern for a decimal number or is 'N/A'.
    
    Args:
    manga_info_list (list): A list of strings containing manga information.
    
    Returns:
    str or None: The first element in the manga info list that matches the regex pattern for a decimal number or is 'N/A', or None if no such element is found.
    """
    return next((element for element in manga_info_list if re.match(r'^\d+(\.\d+)?$', element) or element == 'N/A'), None)


def get_manga_status(manga_info_list):
    """
    Returns the status of a manga given its info list (ex: Ongoing, Completed).

    Args:
        manga_info_list (list): A list containing information about the manga.

    Returns:
        str: The status of the manga (ex: Ongoing, Completed), or None if the list is empty.
    """
    return manga_info_list[1] if len(manga_info_list) > 1 else None


def get_manga_description(manga_info_list):
    """
    Returns the description of a manga from the given manga info list.

    Args:
        manga_info_list (list): A list containing information about a manga.

    Returns:
        str: The description of the manga, or None if the list is empty.
    """
    return manga_info_list[-1] if manga_info_list else None


def create_manga_dict(title, link, status, desc):
    """
    Create a dictionary with manga information.

    Args:
        title (str): The title of the manga.
        link (str): The link to the manga.
        status (str): The status of the manga.
        desc (str): The description of the manga.

    Returns:
        dict: A dictionary containing the manga information.
    """
    return {
        'title': title,
        'link': link,
        'status': status,
        'desc': desc,
    }


def extract_manga_info(manga_card):
    """
    Extracts manga information from a manga card.

    Args:
        manga_card (WebElement): The manga card element.

    Returns:
        dict: A dictionary containing the manga title, link, status, and description.
              Returns None if the manga rating is None.
    """
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


def fetch_and_process_manga_cards(driver, manga_name):
    """
    Fetches manga cards from a given page number and processes them to extract manga info.
    Also creates a progress bar for the manga cards.
    Args:
        driver: The Selenium webdriver instance.
        page_number (int): The page number to fetch manga cards from.

    Returns:
        A list of dictionaries containing manga info.
    """
    manga_cards = fetch_manga_cards(driver, manga_name)
    manga_array = []

    # Create a progress bar for the manga cards
    for manga_card in manga_cards:
        manga_info = extract_manga_info(manga_card)  # Extract the manga info
        if manga_info:  # Check if the manga info is not None
            # Append the manga info to the manga array
            manga_array.append(manga_info)

    return manga_array  # Return the manga array


def handle_no_such_element_exception(logger, page_number, exception):
    """
    Handles a NoSuchElementException that occurred while fetching manga.

    Args:
        logger: The logger object to use for logging the error.
        page_number: The page number where the error occurred.
        exception: The NoSuchElementException that was raised.

    Returns:
        None
    """
    logger.error(f"Error while fetching manga: {exception}")
    # Print an error message
    print(f"No manga cards found on page {page_number}.")


def handle_unexpected_exception(logger, exception):
    """
    Logs an unexpected exception and re-raises it.

    Args:
        logger: The logger to use for logging the error.
        exception: The exception that was raised.

    Raises:
        The original exception that was passed in.
    """
    logger.error(f"An unexpected error occurred: {exception}")
    raise


def process_and_insert_mangas(driver, page_number):
    """
    Fetches and processes manga cards from a given page number using the provided driver,
    then inserts the resulting manga array into the database.

    Args:
        driver: The Selenium webdriver instance to use for fetching the manga cards.
        page_number (int): The page number to fetch the manga cards from.

    Raises:
        NoSuchElementException: If the manga cards cannot be found on the page.
        Exception: For any other unexpected exceptions that occur during execution.
    """
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
    """
    Prompts the user for confirmation and returns their response.

    Args:
        prompt (str): The prompt to display to the user.
        default (str, optional): The default response if the user enters an empty string. Defaults to "y".

    Returns:
        str: The user's response, either 'y' or 'n'.
    """
    while True:
        # Get user input and convert to lowercase
        user_input = input(f"{prompt} ").lower()
        if user_input in ["y", "n", ""]:  # If the input is 'y', 'n' or empty
            return user_input or default  # Return the input
        else:
            print("Invalid input. Please enter 'y' for yes or 'n' for no.")


import random

def generate_random_sleep_threshold(min_threshold, max_threshold):
    """
    Generates a random sleep threshold between the given minimum and maximum values.

    Args:
        min_threshold (float): The minimum sleep threshold value.
        max_threshold (float): The maximum sleep threshold value.

    Returns:
        float: A random sleep threshold value between the given minimum and maximum values.
    """
    return random.randint(min_threshold, max_threshold)


def fetch_and_insert_mangas_with_sleep(driver, page_number, sleep_threshold):
    """
    Fetches and inserts mangas from the specified page number using the given driver object.
    Inserts the mangas into the database and sleeps for a random duration between 0.5 and 2 seconds.
    If the page number is a multiple of the specified sleep threshold, sleeps for a random duration
    between Config.MIN_SLEEP_DURATION and Config.MAX_SLEEP_DURATION seconds instead.

    Args:
        driver: The Selenium webdriver instance to use for fetching the mangas.
        page_number (int): The page number to fetch the mangas from.
        sleep_threshold (int): The page threshold before going to sleep. 

    Returns:
        None
    """
    process_and_insert_mangas(driver, page_number)  # Fetch and insert mangas
    # Sleep for a random duration between 0.5 and 2 seconds
    time.sleep(random.uniform(0.5, 2))

    if page_number % sleep_threshold == 0:  # Check if the page number is a multiple of the sleep threshold
        sleep_duration = random.uniform(
            Config.MIN_SLEEP_DURATION, Config.MAX_SLEEP_DURATION)  # Generate a random sleep duration
        # Sleep for the specified duration
        sleep_for_duration_with_progress(sleep_duration)


import time
from tqdm import tqdm

def sleep_for_duration_with_progress(duration):
    """
    Sleep for a given duration while displaying a progress bar.

    Args:
        duration (float): The duration to sleep for, in seconds.

    Returns:
        None
    """
    # Create a progress bar for the sleep duration and iterate over the range
    for remaining_time in tqdm(range(int(duration)), desc=f"Sleeping for {int(duration)} seconds"):
        time.sleep(1)


def update_sleep_threshold(page_number, current_threshold):
    """
    Update the sleep threshold based on the current page number.

    If the page number is a multiple of the current threshold, generate a new sleep threshold
    between Config.MIN_SLEEP_THRESHOLD and Config.MAX_SLEEP_THRESHOLD.

    Args:
        page_number (int): The current page number.
        current_threshold (int): The current sleep threshold.

    Returns:
        int: The updated sleep threshold.
    """
    if page_number % current_threshold == 0:
        return generate_random_sleep_threshold(
            Config.MIN_SLEEP_THRESHOLD, Config.MAX_SLEEP_THRESHOLD)
    return current_threshold


def process_manga(driver):
    """
    Fetches and inserts manga data from multiple pages using the given driver.

    Args:
        driver: The Selenium WebDriver instance to use for fetching data.

    Returns:
        None
    """
    sleep_threshold = generate_random_sleep_threshold(
        Config.MIN_SLEEP_THRESHOLD, Config.MAX_SLEEP_THRESHOLD)  # Generate a random sleep threshold
    for page_number in range(1, Config.TOTAL_PAGES + 1):
        fetch_and_insert_mangas_with_sleep(
            driver, page_number, sleep_threshold)  # Fetch and insert mangas
        sleep_threshold = update_sleep_threshold(
            page_number, sleep_threshold)  # Update the sleep threshold


def handle_user_confirmation():
    """
    Asks the user for confirmation to add manga names to the database.

    Returns:
        str: The user's input (either 'y' or 'n').
    """
    return get_user_confirmation(
        "Do you want to add manga names to the database? (Y/n): ", default="y")


def setup_driver_if_needed(update_symbols):
    """
    Set up the driver if the user wants to update the database.

    Args:
        update_symbols (str): A string indicating whether the user wants to update the database.

    Returns:
        The driver object if the user wants to update the database, otherwise None.
    """
    return driver_setup() if update_symbols != "n" else None


def perform_main_workflow(driver):
    """
    Performs the main workflow for fetching manga pages, detecting duplicates, and removing doujinshi.

    Args:
        driver: The Selenium WebDriver instance to use for fetching manga pages.

    Returns:
        None
    """
    if driver:  # Check if the driver is initialized
        process_manga(driver)  # Process the manga pages
        detect_duplicates()  # Detect and remove duplicates
        remove_doujinshi()  # Remove doujinshi from the database (fan-made manga)


def cleanup(driver):
    """
    Closes the browser window.

    Args:
    driver: The webdriver instance to be closed.

    Returns:
    None
    """
    if driver:
        driver.quit()  # Close the browser window


def main():
    """
    The main function that handles the fetching and inserting of mangas.

    This function first prompts the user for confirmation to update symbols, sets up the driver if needed,
    and then performs the main workflow. If an unexpected exception occurs, it is handled and logged.
    """
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