import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException, WebDriverException, TimeoutException,  NoSuchWindowException, InvalidSessionIdException
from dotenv import load_dotenv
import time
import requests
import re
import json
from Config.config import Config
import base64
import hashlib
from Config.logs_config import setup_logging
from MangaDownload.WebInteractions import WebInteractions
# Configure logging
from MangaDownload.WebInteractions import logger
from Driver.driver_config import driver_setup
import random
from PIL import Image
import io
import urllib.request


class FileOperations:
    failed_images = []  # Array to store the images that failed to save

    def __init__(self, web_interactions):
        """Initialize the FileOperations instance. 

        Args:
            web_interactions (WebInteractions): The WebInteractions instance.
            driver (WebDriver): The Selenium WebDriver instance.
        """
        # Initialize the WebInteractions instance
        self.web_interactions = web_interactions
        # Initialize the WebDriver instance
        self.driver = web_interactions.driver
        # Store the original tab handle
        self.original_tab_handles = None
        # Store the last processed URL
        self.last_processed_url = None
        # Store the unique base64 data (to avoid duplicates)
        self.unique_base64_data = set()
        # Store the last loaded image source (to check if the image is loaded)
        self.last_loaded_img_src = None

    def sanitize_folder_name(self, folder_name):
        """Function to sanitize the folder name. This means that the folder name will be stripped of any characters that are not allowed in a folder name.

        Args:
            folder_name (string): The folder name to sanitize. 

        Returns:
            string: The sanitized folder name.
        """
        # Replace characters not allowed in a folder name with a space
        sanitized_name = re.sub(r'[<>:"/\\|?*]', ' ', folder_name)
        sanitized_name = sanitized_name.strip()  # Remove leading and trailing spaces
        if not sanitized_name:
            # Set the folder name to "UnknownManga" if it's empty
            sanitized_name = "UnknownManga"
        return sanitized_name

    def create_folder_path(self, save_path, sanitized_folder_name, chapter_number):
        """Function to generate the folder path. This will be used to save the manga chapters.

        Args:
            save_path (string): The path to save the manga.
            sanitized_folder_name (string): The sanitized folder name.
            chapter_number (int): The chapter number.

        Returns:
            string: The folder path.
        """
        return os.path.join(save_path, sanitized_folder_name, chapter_number)

    def create_screenshot_filename(self, page_number):
        """Generate the screenshot filename. (eg: page_1.png)

        Args:
            page_number (int): The page number.

        Returns:
            string: The screenshot filename.
        """
        return f"page_{page_number}.png"

    def create_screenshot_filepath(self, folder_path, screenshot_filename):
        """Function to generate the screenshot filepath. This will be used to save the screenshot.

        Args:
            folder_path (string): The folder path to save the screenshot.
            screenshot_filename (string): The screenshot filename.

        Returns:
            string: The screenshot filepath.
        """
        return os.path.join(folder_path, screenshot_filename)

    def create_chapter_folder(self, save_path, series_name, chapter_number, page_number=None):
        """Function to create the folder path and screenshot filepath for a chapter.
        This function also creates the folder if it doesn't exist.


        Args:
            save_path (string): The path to save the manga.
            series_name (string): The name of the manga series.
            chapter_number (string): The chapter number. (ex: Chapter 1)
            page_number (int, optional): The page number. Defaults to None.

        Returns:
            _type_: _description_
        """
        folder_path = self.create_folder_path(
            save_path, self.sanitize_folder_name(series_name), "Chapter " + str(chapter_number))  # Create the folder path

        if not os.path.exists(folder_path):  # If the folder doesn't exist
            os.makedirs(folder_path)   # Create the folder if it doesn't exist

        if page_number is not None:  # If the page number is provided
            screenshot_filename = self.create_screenshot_filename(
                page_number)  # Create the screenshot filename
            screenshot_filepath = self.create_screenshot_filepath(
                folder_path, screenshot_filename)  # Create the screenshot filepath
            # Return the folder path and screenshot filepath
            # screenshot_filepath is used in the delete_last_page function
            return folder_path, screenshot_filepath
        else:
            return folder_path  # Return the folder path

    def take_screenshot(self, driver, save_path, series_name, chapter_number, page_number, img_src):
        """
        Takes a screenshot of a manga page and saves it to disk.

        Args:
            driver (WebDriver): The WebDriver instance to use for taking the screenshot.
            save_path (str): The path to the directory where the screenshot should be saved.
            series_name (str): The name of the manga series.
            chapter_number (int): The number of the chapter.
            page_number (int): The number of the page.
            img_src (str): The URL of the manga page image.

        Returns:
            None
        """
        folder_path, _ = self.create_chapter_folder(
            save_path, series_name, chapter_number, page_number)  # Create the folder path and screenshot filepath
        # Get the image data from the image source (blob URL)
        img_data = self.get_image_data(driver, img_src)
        if img_data:
            try:
                # Save the screenshot
                self.save_image(img_data, folder_path, self.create_screenshot_filename(page_number), page_number)
                return page_number + 1
            except Exception as e:
                logger.error(f"Error saving image: {e}")
                raise
        else:
            return page_number
    def save_png_links(self, save_path, series_name, chapter_number, page_number, img_src):
        folder_path, _ = self.create_chapter_folder(save_path, series_name, chapter_number, page_number)
        self.save_image_from_url(img_src, folder_path, self.create_screenshot_filename(page_number))
        return page_number + 1

    def save_image_from_url(self, img_src, folder_path, file_name):
        response = requests.get(img_src)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            image.save(os.path.join(folder_path, file_name))
            return True
        else:
            return False

    def save_image(self, img_data, folder_path, file_name, index):
        """Function to save the image data to a file. If the image is too large, it is split into chunks and saved.

        Args:
            img_data (string): The base64 data of the image.
            folder_path (string): The folder path to save the image.
            file_name (string): The file name of the image that will be saved. (ex: page_1.png)
            index (int): The index of the image. 
        """
        try:
            image_data = base64.b64decode(img_data.split(',')[1])
            # Save the image as-is
            self.write_image(image_data, folder_path, file_name)
        except NoSuchWindowException:
            # Handle the "no such window" exception
            logger.error(f"Window closed for sub-div {index + 1}")
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise

    def fetch_base64_data(self, driver, img_src):
        """Fetch the base64 data from the image source. This is done using JavaScript. The image source is a blob URL,
        which means that the image data is not directly accessible. 
        So, we use JavaScript to fetch the image data and return it as a base64 string.


        Args:
            driver (WebDriver) : The Selenium WebDriver instance.
            img_src (string) : The image source. 

        Returns:
            string: The base64 data of the image.
        """
        return driver.execute_script(
            f"return fetch('{img_src}').then(response => response.blob()).then(blob => new Promise((resolve, reject) => {{const reader = new FileReader(); reader.onloadend = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(blob);}}))")

    def extract_base64_part(self, base64_data):
        """ Extract the base64 from the data URL. (eg: data:image/png;base64,base64_data -> base64_data) 

        Args:
            base64_data (string): The data URL.

        Returns:
            string: The base64 part of the data URL.
        """
        return base64_data.split(',')[1]  # Extract the base64 part

    def add_padding(self, base64_data):
        """Add padding to the base64 part of the data URL. (eg: base64_data -> base64_data + padding) 
        The padding is added to the base64 part to make the length of the base64 part a multiple of 4.
        Since having a length that is not a multiple of 4 can cause issues while decoding the base64 data.

        Args:
            base64_data (string): The base64 part of the data URL.

        Returns:
            string: The base64 part of the data URL with padding.
        """
        padding = '=' * (len(base64_data) % 4)
        return base64_data + padding  # Add padding to the base64 part

    def construct_data_url(self, base64_data):
        """Construct an url from the base64 data. (eg: base64_data -> data:image/png;base64,base64_data)

        Args:
            base64_data (_type_): _description_

        Returns:
            _type_: _description_
        """
        return f"data:image/png;base64,{base64_data}"  # Construct the data URL

    def handle_duplicates(self, data_url):
        """Function to detect if there are any duplicates in the base64 urls. This is done by storing the base64 data in a set.

        Args:
            data_url (string): The data URL.

        Returns:
            bool: True if the data URL is a duplicate, False otherwise.
        """
        if data_url in self.unique_base64_data:

            return True
        else:
            # Add the data URL to the set of unique base64 data
            self.unique_base64_data.add(data_url)
            return False

    def get_image_data(self, driver, img_src):
        try:
            base64_data = self.construct_data_url(
                self.add_padding(
                    self.extract_base64_part(
                        self.fetch_base64_data(driver, img_src)
                )))
                

            if self.handle_duplicates(base64_data):
                # If the data URL is a duplicate, return None
                return None
            else:
                return base64_data  # Return the data URL
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def delete_last_page(self, save_path, series_name, chapter_number, page_number):
        _, screenshot_filepath = self.create_chapter_folder(
            save_path, series_name, chapter_number, page_number)  # Create the folder path and screenshot filepath
        try:
            os.remove(screenshot_filepath)  # Delete the last page
        except Exception as e:
            logger.error(f"Error deleting screenshot: {e}")
