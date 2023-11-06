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
from config import Config
import base64
import hashlib
from logs_config import setup_logging
from MangaDownload.WebInteractions import WebInteractions
# Configure logging 
from MangaDownload.WebInteractions import logger

class FileOperations:
    failed_images = []  # Array to store the images that failed to save

    def __init__(self, web_interactions, driver):
        self.web_interactions = web_interactions
        self.driver = driver
        self.original_tab_handles = None
        self.last_processed_url = None
        self.unique_base64_data = set()
        self.last_loaded_img_src = None

    def sanitize_folder_name(self, folder_name):
        # Replace characters not allowed in a folder name with a space
        sanitized_name = re.sub(r'[<>:"/\\|?*]', ' ', folder_name)
        # Remove leading and trailing spaces
        sanitized_name = sanitized_name.strip()
        if not sanitized_name:
            sanitized_name = "UnknownManga"
        return sanitized_name

    def create_chapter_folder(self, save_path, series_name, chapter_number, page_number=None):
        # Sanitize the folder name (remove characters not allowed in a folder name)
        sanitized_folder_name = self.sanitize_folder_name(series_name)
        folder_path = os.path.join(
            save_path, sanitized_folder_name, str(chapter_number))

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        if page_number is not None:
            # Create the filename for the screenshot (example: page_1.png)
            screenshot_filename = f"page_{page_number}.png"
            # Create the full path for the screenshot (example: C:\Users\user\Documents\Manga\Series Name\1\page_1.png)
            screenshot_filepath = os.path.join(
                folder_path, screenshot_filename)
            return folder_path, screenshot_filepath
        else:
            return folder_path

    def save_screenshot(self, driver, save_path, series_name, chapter_number, page_number):
        folder_path, screenshot_filepath = self.create_chapter_folder(
            save_path, series_name, chapter_number, page_number)
        try:
            elements = driver.find_elements(By.CLASS_NAME, Config.MANGA_IMAGE)
            if elements:
                elements[0].screenshot(screenshot_filepath)
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            raise


    def save_long_screenshot(self, driver, save_path, series_name, chapter_number, page_number):
        try:
            parent_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'mx-auto.h-full.w-full'))
            )
            folder_path = self.create_chapter_folder(
                save_path, series_name, chapter_number, page_number)
            # higher sleep time to allow the page to load completely
            time.sleep(10)
            sub_divs = parent_div.find_elements(
                By.CLASS_NAME, 'md--page.ls.limit-width.mx-auto')
            print(f"Found {len(sub_divs)} sub-divs")

            # Fetch all image data URLs
            img_data_list = [self.get_image_data(driver, sub_div.find_element(
                By.TAG_NAME, Config.IMG).get_attribute(Config.SRC)) for sub_div in sub_divs]
            # array for the images that failed to save
            # failed_to_save = []
            print(f"Found {len(img_data_list)} image data URLs")

            # Maximum number of pages to save before resetting the driver (to avoid memory issues)
            MAX_PAGES_BEFORE_RESET = 20

            for i, img_data in enumerate(img_data_list):
                try:
                    # Check if it's time to reset the driver
                    if (i + 1) % MAX_PAGES_BEFORE_RESET == 0:
                        # refresh the page
                        driver.refresh()
                        time.sleep(5)  # Wait for the page to load after reset
                    index = i + 1
                    file_name = f"page_{index}.png"
                    self.save_image(driver, img_data,
                                    folder_path, file_name, index)

                except Exception as img_error:
                    logger.error(f"Error saving image {index}: {img_error}")
                    self.failed_images.append({
                        'index': index,
                        'img_src': sub_divs[i].find_element(By.TAG_NAME, Config.IMG).get_attribute(Config.SRC),
                        'file_name': file_name,
                        'folder_path': folder_path
                    })
            # Retry the process for the images that failed to save (if any)
            self.retry_unsaved_images(driver)
            # reset the unique base64 data set
            self.unique_base64_data = set()
        except Exception as e:
            logger.error(f"Error saving long screenshot: {e}")
            raise

    def save_image(self, driver, img_data, folder_path, file_name, index):
        try:
            if img_data:
                # Check if the URL is the same as the last processed URL
                current_url = driver.current_url

                # Wait for the page to load
                driver.get(img_data)
                time.sleep(4)

                # Handle stale element reference exception
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, Config.IMG)))
                except StaleElementReferenceException:
                    logger.warning(
                        "Stale element reference. Refreshing the page.")
                    driver.refresh()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, Config.IMG)))

                # Update the last processed URL
                self.last_processed_url = driver.current_url
                if current_url == self.last_processed_url:
                    logger.warning(
                        f"Duplicate URL detected, but continuing with sub-div {index + 1}")
                    
                # Save the image
                self.save_image_in_tab(driver, folder_path, file_name, index)

            else:
                logger.warning(
                    f"Skipping sub-div {index + 1} - Empty image data")

        except NoSuchWindowException:
            # Handle the "no such window" exception
            logger.error(f"Window closed for sub-div {index + 1}")
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise

    def save_image_in_tab(self, driver, folder_path, file_name, index):
        try:
            # Locate the img element dynamically
            img_locator = (By.TAG_NAME, Config.IMG)
            # call the wait until image loaded function
            self.web_interactions.wait_until_image_loaded(self.last_loaded_img_src)

            # Attempt to locate the image element, handle stale element reference if needed
            img = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(img_locator))

            file_path = os.path.join(folder_path, file_name)
            img.screenshot(file_path)

            logger.info(f"Screenshot for page {index} saved")

        except StaleElementReferenceException:
            logger.error(
                f"Stale element reference while saving image for page {index}")
        except TimeoutException:
            logger.error(
                f"Timeout waiting for image element for page {index}")
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise

    def retry_unsaved_images(self, driver):
        for failed_image in self.failed_images:
            img_data = failed_image['img_data']
            folder_path = failed_image['folder_path']
            file_name = failed_image['file_name']
            index = failed_image['index']

            try:
                self.save_image(driver, img_data,
                                folder_path, file_name, index)
                # If the image is saved successfully, remove it from the failed images list
                self.failed_images.remove(failed_image)
            except Exception as img_error:
                logger.error(f"Error saving image {index}: {img_error}")

        # If there are still failed images, retry the process for them
        if self.failed_images:
            logger.warning("Retrying failed images...")
            self.retry_unsaved_images(driver)
        else:
            logger.info("All images saved successfully.")

    def get_image_data(self, driver, img_src):
        try:
            print(f"Fetching image data for {img_src}")
            # Execute JavaScript to fetch the image data as base64
            base64_data = driver.execute_script(
                f"return fetch('{img_src}').then(response => response.blob()).then(blob => new Promise((resolve, reject) => {{const reader = new FileReader(); reader.onloadend = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(blob);}}))")

            # Extract the base64 part after the comma
            base64_data = base64_data.split(',')[1]

            # Add padding if needed
            padding = '=' * (len(base64_data) % 4)
            base64_data += padding

            # Construct the Data URL
            data_url = f"data:image/png;base64,{base64_data}"

            # Check for duplicates
            if data_url in self.unique_base64_data:
                print("Duplicate found. Regenerating base64 link...")
                return self.get_image_data(driver, img_src)
            else:
                # Add the generated base64 link to the set
                self.unique_base64_data.add(data_url)
                return data_url

        except WebDriverException as e:
            logger.error(
                f"Error executing JavaScript or taking screenshot - {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def delete_last_page(self, save_path, series_name, chapter_number, page_number):
        _, screenshot_filepath = self.create_chapter_folder(
            save_path, series_name, chapter_number, page_number)
        try:
            os.remove(screenshot_filepath)  # Delete the last page
        except Exception as e:
            logger.error(f"Error deleting screenshot: {e}")

