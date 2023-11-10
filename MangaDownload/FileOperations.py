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
        """Initialize the FileOperations instance. 
    
        Args:
            web_interactions (WebInteractions): The WebInteractions instance.
            driver (WebDriver): The Selenium WebDriver instance.
        """
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
        return os.path.join(save_path, sanitized_folder_name, str(chapter_number))

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
        sanitized_folder_name = self.sanitize_folder_name(
            series_name)  # Sanitize the folder name
        folder_path = self.create_folder_path(
            save_path, sanitized_folder_name, chapter_number)  # Create the folder path

        if not os.path.exists(folder_path):  # If the folder doesn't exist
            os.makedirs(folder_path)   # Create the folder if it doesn't exist

        if page_number is not None:  # If the page number is provided
            screenshot_filename = self.create_screenshot_filename(
                page_number)  # Create the screenshot filename
            print(screenshot_filename)
            screenshot_filepath = self.create_screenshot_filepath(
                folder_path, screenshot_filename)  # Create the screenshot filepath
            # Return the folder path and screenshot filepath
            return folder_path, screenshot_filepath # screenshot_filepath is used in the delete_last_page function
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
            img_data = self.get_image_data(driver, img_src) # Get the image data from the image source (blob URL)
            if img_data:
                try:
                    file_name = self.create_screenshot_filename(page_number)  # Create the screenshot filename
                    # Save the screenshot
                    self.save_image(img_data, folder_path, file_name, page_number)
                except Exception as e:
                    logger.error(f"Error saving image: {e}")
                    raise


    def find_parent_div(self, driver):
        """Function to find the parent div in a long manga page. A long manga page is a single page that contains all of the chapter.
        This function also waits until all of the sub-divs are loaded completely before continuing. 

        Args:
            driver (WebDriver): The Selenium WebDriver instance.

        Returns:
            WebElement: The parent div element.
        """
        time.sleep(10)
        # Find the parent div
        parent_div = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, Config.LONG_MANGA_PARENT_DIV)))
        
        # log all of the sub div class name of the parent_div
        sub_divs = parent_div.find_elements(By.XPATH, ".//*")
        for sub_div in sub_divs:
            logger.info(f"Sub div class name: {sub_div.get_attribute('class')}")
        
        # Wait until there are no more elements with class name 'unloaded mx-auto' and 'flex justify-center items-center p-2 text-primary overflow-hidden w-full mx-auto'
        while True:
            unloaded_elements = parent_div.find_elements(By.CSS_SELECTOR, '.unloaded.mx-auto')
            #flex_elements = parent_div.find_elements(By.CSS_SELECTOR, '.flex.justify-center.items-center.p-2.text-primary.overflow-hidden.w-full.mx-auto')
            if not unloaded_elements:
                break
            time.sleep(1)
            parent_div = driver.find_element(By.CLASS_NAME, Config.LONG_MANGA_PARENT_DIV)
        return parent_div
        




    def find_sub_divs(self, driver):
        """Function to find all sub-divs in a long manga page. A long manga page is a single page that contains all of the chapter.
        Inside the parent div, there are multiple sub-divs. Each sub-div contains a part of the chapter.

        Args:
            driver (WebDriver): The Selenium WebDriver instance.

        Returns:
            list: A list of all sub-divs from the parent-div.
        """
        # Find all sub-divs
        return self.find_parent_div(driver).find_elements(By.CLASS_NAME, Config.LONG_MANGA_SUBDIV)

    def save_long_screenshot(self, driver, save_path, series_name, chapter_number, page_number):
        """Function to save a screenshot of a long manga page.
           A long manga page is a single page that contains all of the chapter.
           

        Args:
            driver (WebDriver): The Selenium WebDriver instance.
            save_path (string): The path to save the manga.
            series_name (string): The name of the manga series.
            chapter_number (string): The chapter number. (ex: Chapter 1)
            page_number (int): The page number. (ex: 1)
        """
        try:
            # Create the folder path
            folder_path = self.create_chapter_folder(
                save_path, series_name, chapter_number, page_number)
            # Find all sub-divs
            sub_divs = self.find_sub_divs(driver)

            # Fetch all image data URLs
            print(f"found {len(sub_divs)} sub-divs")
            img_data_list = [self.get_image_data(driver, sub_div.find_element(
                By.TAG_NAME, Config.IMG).get_attribute(Config.SRC)) for sub_div in sub_divs]

            for i, img_data in enumerate(img_data_list):
                try:
                    # Variable to store the index of the image
                    index = i + 1
                    if img_data:  
                        # Create the file name (e.g. page_1.png)
                        file_name = self.create_screenshot_filename(index)
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
        
    def write_image(self, image_data, folder_path, file_name):
        """Function to write the image data to a file. Creating the file is done using the "with" statement.

        Args:
            image_data (string): The base64 data of the image.
            folder_path (string): The folder path to save the image.
            file_name (string): The file name of the image that will be saved. (ex: page_1.png)
        """
        with open(os.path.join(folder_path, file_name), 'wb') as file:
            file.write(image_data)

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
                    self.write_image(image_data, folder_path, file_name)
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
            file_name_removed_extension = file_name.split('.')[0]
            # Save each chunk with a unique file name
            chunk_file_name = f"{file_name_removed_extension}_part_{i // chunk_height}.png"
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
