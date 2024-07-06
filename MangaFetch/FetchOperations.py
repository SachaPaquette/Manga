import re
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
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


def wait_for_page_to_load(driver, timeout=5):
    """
    Waits for the page to load by checking if the manga cards are present.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        None
    """
    # Wait until the manga cards are present on the page
    WebDriverWait(driver, timeout).until(lambda d: d.find_elements(by=By.CLASS_NAME, value='manga-card'))

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
    navigate_to_manga_url(driver, format_manga_url(manga_name))  # Navigate to the manga url
    wait_for_page_to_load(driver)  # Wait for the page to load
    return find_manga_cards(driver)  # Return the manga cards


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


def create_manga_dict(title, link):
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
    manga_info_list = get_manga_info_list(manga_card)  # Get the manga info list
    if manga_info_list:
        return create_manga_dict(manga_info_list[0], manga_link)
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

