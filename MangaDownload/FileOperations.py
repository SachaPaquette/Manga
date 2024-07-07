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

import concurrent.futures
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
        
        if os.getenv("SAVE_PATH") is not None:
            self.save_path = os.getenv("SAVE_PATH")
        else:
            print("SAVE_PATH environment variable not found.")
            self.save_path = Config.DEFAULT_SAVE_PATH
            print(f"Using default save path to save mangas: {self.save_path}")

    def sanitize_folder_name(self, folder_name):
        """
        Sanitize the folder name by removing or replacing any characters that are not allowed in a folder name.

        Args:
            folder_name (str): The folder name to sanitize.

        Returns:
            str: The sanitized folder name.
        """
        # Replace invalid characters with a space and strip leading/trailing spaces
        sanitized_name = re.sub(r'[<>:"/\\|?*]', ' ', folder_name).strip()

        # Set the folder name to "UnknownManga" if it is empty after sanitization
        return sanitized_name if sanitized_name else "UnknownManga"


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
        """
        Creates the folder path for a chapter and optionally the screenshot filepath for a page.
        This function also creates the folder if it doesn't exist.

        Args:
            save_path (str): The path to save the manga.
            series_name (str): The name of the manga series.
            chapter_number (str): The chapter number. (e.g., Chapter 1)
            page_number (int, optional): The page number. Defaults to None.

        Returns:
            tuple: A tuple containing the folder path and optionally the screenshot filepath.
        """
        # Sanitize the series name and create the folder path
        folder_path = self.create_folder_path(save_path, self.sanitize_folder_name(series_name), f"Chapter {chapter_number}")
        # Create the folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        # If page number is provided, create the screenshot filepath
        if page_number:
            return folder_path, self.create_screenshot_filepath(folder_path, self.create_screenshot_filename(page_number))
        return folder_path

    def save_png_links(self, save_path, series_name, chapter_number, page_number, img_src):
        """
        Save a PNG image from a URL to the specified folder path, using the chapter and page numbers.

        Args:
            save_path (str): The path to save the manga.
            series_name (str): The name of the manga series.
            chapter_number (int or str): The chapter number.
            page_number (int): The page number.
            img_src (str): The URL of the PNG image to save.

        Returns:
            int: The next page number.
        """
        try:
            folder_path, _ = self.create_chapter_folder(save_path, series_name, chapter_number, page_number)
            self.save_image_from_url(img_src, folder_path, self.create_screenshot_filename(page_number))
            return page_number + 1
        except Exception as e:
            logger.error(f"Error saving PNG link {img_src} for chapter {chapter_number}, page {page_number}: {e}")
            return page_number  # Return the current page number if there's an error

    def bulk_save_png_links(self, save_path, page_data):
        """
        Save multiple PNG images from URLs to the specified folder path in bulk.

        Args:
            save_path (str): The path to save the manga.
            page_data (list): A list of tuples containing series name, chapter number, page number, and image URL.

        Returns:
            None
        """
        def process_image(data):
            series_name, chapter_number, page_number, img_src = data
            try:
                folder_path, _ = self.create_chapter_folder(save_path, series_name, chapter_number, page_number)
                self.save_image_from_url(img_src, folder_path, self.create_screenshot_filename(page_number))
            except Exception as e:
                logger.error(f"Error saving PNG link {img_src} for chapter {chapter_number}, page {page_number}: {e}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(process_image, page_data)

    def save_chapter_pages(self, series_name, chapter_number, pages):
        """
        Save the captured PNG links for the chapter.

        Args:
            series_name (str): The name of the manga series.
            chapter_number (int): The number of the chapter.
            pages (list): A list of tuples containing page numbers and URLs.

        Returns:
            None
        """
        page_data = []

        for page_number, page_url in pages:
            page_data.append((series_name, chapter_number, page_number, page_url ))
        print(f"Saving {len(page_data)} pages for chapter {chapter_number}...")
        self.bulk_save_png_links(self.save_path, page_data)
        
        
    def save_image_from_url(self, img_src, folder_path, file_name):
        """
        Downloads an image from the given URL and saves it to the specified folder with the given file name.

        Args:
            img_src (str): The URL of the image to download.
            folder_path (str): The path to the folder where the image will be saved.
            file_name (str): The name to save the image file as.

        Returns:
            bool: True if the image was successfully saved, False otherwise.
        """
        try:
            response = requests.get(img_src)
            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
            # Save the image to the specified folder
            Image.open(io.BytesIO(response.content)).save(os.path.join(folder_path, file_name))
            return True
        except requests.RequestException as e:
            logger.error(f"Error downloading image from {img_src}: {e}")
            return False
        except IOError as e:
            logger.error(f"Error saving image to {os.path.join(folder_path, file_name)}: {e}")
            return False
