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
from database import find_mangas
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
class FileOperations:
    failed_images = []  # Array to store the images that failed to save

    def __init__(self, web_interactions, driver):
        # Initialize the WebInteractions instance
        self.web_interactions = web_interactions
        # Initialize the WebDriver instance
        self.driver = driver
        # Store the original tab handle
        self.original_tab_handles = None
        # Store the last processed URL
        self.last_processed_url = None
        # Store the unique base64 data (to avoid duplicates)
        self.unique_base64_data = set()
        # Store the last loaded image source (to check if the image is loaded)
        self.last_loaded_img_src = None

    def sanitize_folder_name(self, folder_name):
        # Replace characters not allowed in a folder name with a space
        sanitized_name = re.sub(r'[<>:"/\\|?*]', ' ', folder_name)
        sanitized_name = sanitized_name.strip()  # Remove leading and trailing spaces
        if not sanitized_name:
            # Set the folder name to "UnknownManga" if it's empty
            sanitized_name = "UnknownManga"
        return sanitized_name

    def create_folder_path(self, save_path, sanitized_folder_name, chapter_number):
        # Create the folder path
        return os.path.join(save_path, sanitized_folder_name, str(chapter_number))

    def create_screenshot_filename(self, page_number):
        return f"page_{page_number}.png"  # Create the screenshot filename

    def create_screenshot_filepath(self, folder_path, screenshot_filename):
        # Create the screenshot filepath
        return os.path.join(folder_path, screenshot_filename)

    def create_chapter_folder(self, save_path, series_name, chapter_number, page_number=None):
        sanitized_folder_name = self.sanitize_folder_name(
            series_name)  # Sanitize the folder name
        folder_path = self.create_folder_path(
            save_path, sanitized_folder_name, chapter_number)  # Create the folder path

        if not os.path.exists(folder_path):  # If the folder doesn't exist
            os.makedirs(folder_path)   # Create the folder if it doesn't exist

        if page_number is not None:  # If the page number is provided
            screenshot_filename = self.create_screenshot_filename(
                page_number)  # Create the screenshot filename
            screenshot_filepath = self.create_screenshot_filepath(
                folder_path, screenshot_filename)  # Create the screenshot filepath
            # Return the folder path and screenshot filepath
            return folder_path, screenshot_filepath
        else:
            return folder_path  # Return the folder path

    def find_manga_image(self, driver):
        # Find the manga image
        return driver.find_elements(By.CLASS_NAME, Config.MANGA_IMAGE)

    def screensave(self, elements, screenshot_filepath):
        try:
            elements[0].screenshot(screenshot_filepath)  # Save the screenshot
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")

    def take_screenshot(self, driver, save_path, series_name, chapter_number, page_number):
        _, screenshot_filepath = self.create_chapter_folder(
            save_path, series_name, chapter_number, page_number)  # Create the folder path and screenshot filepath
        try:
            elements = self.find_manga_image(driver)  # Find the manga image
            if elements:  # If the manga image is found
                # Save the screenshot
                self.screensave(elements, screenshot_filepath)
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            raise

    def find_parent_div(self, driver):
        # Wait for the parent div to load
        return WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, Config.LONG_MANGA_PARENT_DIV)))

    def find_sub_divs(self, driver):
        # Wait for the parent div to completely load (to avoid missing sub-divs)
        time.sleep(10)
        # Find all sub-divs
        return self.find_parent_div(driver).find_elements(By.CLASS_NAME, Config.LONG_MANGA_SUBDIV)

    def save_long_screenshot(self, driver, save_path, series_name, chapter_number, page_number):
        try:
            # Create the folder path
            folder_path = self.create_chapter_folder(
                save_path, series_name, chapter_number, page_number)
            # Find all sub-divs
            sub_divs = self.find_sub_divs(driver)

            # Fetch all image data URLs
            img_data_list = [self.get_image_data(driver, sub_div.find_element(
                By.TAG_NAME, Config.IMG).get_attribute(Config.SRC)) for sub_div in sub_divs]

            for i, img_data in enumerate(img_data_list):
                try:
                    # Variable to store the index of the image
                    index = i + 1
                    if img_data is None:
                        # If the image data is None, skip it
                        logger.warning(f"Skipping image {index} due to None data URL.")
                        continue
                    # Create the file name (e.g. page_1.png)
                    file_name = f"page_{index}.png"
                    # Save the image
                    self.save_image(img_data,
                                    folder_path, file_name, index)
                except Exception as img_error:
                    logger.error(f"Error saving image {index}: {img_error}")

            # reset the unique base64 data set
            self.unique_base64_data = set()
        except Exception as e:
            logger.error(f"Error saving long screenshot: {e}")
            raise
        except KeyboardInterrupt:
            print("Exiting...")
            raise
    def save_image(self, img_data, folder_path, file_name, index):
        """Function to save the image data to a file. If the image is too large, it is split into chunks and saved.
        
        Args:
            img_data (string): The base64 data of the image.
            folder_path (string): The folder path to save the image.
            file_name (string): The file name of the image that will be saved. (ex: page_1.png)
            index (int): The index of the image. 
        """
        try:
            if img_data:
                image_data = base64.b64decode(img_data.split(',')[1])
                img = Image.open(io.BytesIO(image_data))

                # Check the height of the image
                img_height = img.size[1]

                if img_height > 2000:
                    # Split the image into chunks
                    chunk_height = 2000
                    self.split_image(img, folder_path, file_name, chunk_height)
                else:
                    # Save the image as-is
                    with open(os.path.join(folder_path, file_name), 'wb') as file:
                        file.write(image_data)

            else:
                logger.error(f"Image data not found for page {index}")
        except NoSuchWindowException:
            # Handle the "no such window" exception
            logger.error(f"Window closed for sub-div {index + 1}")
        except KeyboardInterrupt:
            print("Exiting...")
            raise
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise

    def split_image(self, img, folder_path, file_name, chunk_height):
        """This function splits an image into chunks of the specified height and saves each chunk as a separate image.
        This is done to avoid having a single image that is too large.

        Args:
            img (Image): The image to split into chunks.
            folder_path (string): The folder path to save the image chunks.
            file_name (string): The file name of the image that wiil be saved in chunks. (ex: page_1.png)
            chunk_height (int): The height of each image chunk.
        """
        # Get the width and height of the image
        width, height = img.size
        # Split the image into chunks
        for i in range(0, height, chunk_height):
            box = (0, i, width, min(i + chunk_height, height))
            chunk = img.crop(box)

            # Save each chunk with a unique file name
            chunk_file_name = f"part_{i // chunk_height}_{file_name}"
            with open(os.path.join(folder_path, chunk_file_name), 'wb') as file:
                # Save the image chunk
                chunk.save(file)


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
        if data_url in self.unique_base64_data:
            print("Duplicate found. Regenerating base64 link...")
            return True
        else:
            # Add the data URL to the set of unique base64 data
            self.unique_base64_data.add(data_url)
            return False

    def get_image_data(self, driver, img_src):
        try:
            print(f"Fetching image data for {img_src}")
            base64_data = self.fetch_base64_data(
                driver, img_src)  # Fetch the base64 data
            base64_part = self.extract_base64_part(
                base64_data)  # Extract the base64 part
            padded_base64_data = self.add_padding(
                base64_part)  # Add padding to the base64 part
            data_url = self.construct_data_url(
                padded_base64_data)  # Construct the data URL

            if self.handle_duplicates(data_url):
                # If the data URL is a duplicate, return None
                return None
            else:
                return data_url  # Return the data URL

        except WebDriverException as e:
            logger.error(
                f"Error executing JavaScript or taking screenshot - {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def delete_last_page(self, save_path, series_name, chapter_number, page_number):
        _, screenshot_filepath = self.create_chapter_folder(
            save_path, series_name, chapter_number, page_number)  # Create the folder path and screenshot filepath
        try:
            os.remove(screenshot_filepath)  # Delete the last page
        except Exception as e:
            logger.error(f"Error deleting screenshot: {e}")
