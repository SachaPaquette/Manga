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

logger = setup_logging('manga_download', Config.MANGA_DOWNLOAD_LOG_PATH)


class WebInteractions:
    def __init__(self):
        self.driver = self.setup_driver()  # Initialize the WebDriver instance
        self.original_tab_handle = None  # Store the original tab handle
        self.last_loaded_img_src = None  # Store the last loaded image source

    def setup_driver(self):
        # Set up and return the WebDriver instance
        options = webdriver.ChromeOptions()

        # options.add_argument('--headless')

        # Disable logging (i.e., hide the "DevTools listening on..." message)
        options.add_argument("--log-level=3")

        driver = webdriver.Chrome(options=options)

        return driver

    def cleanup(self):
        self.driver.quit()  # Close the browser window
        print("Resources cleaned up.")

    def is_button_clickable(self, button):
        # current button layout is button > span > svg - we currently have the svg element
        span_element = button.find_element(
            By.XPATH, '..')  # Get the span element
        button_element = span_element.find_element(
            By.XPATH, '..')  # Get the button element
        button_class = button_element.get_attribute('class')
        # Check if the button element is disabled
        logger.info(f"Button class: {button_class}")
        if 'disabled' in button_class:
            # Button is disabled, return False to break out of the loop
            return False
        # Button is enabled, return True
        return True

    def click_next_page(self):
        try:

            # Check if the next page button is clickable and click it
            if self.is_button_clickable(self.driver.find_element(By.CLASS_NAME, Config.NEXT_PAGE_BUTTON)):
                ActionChains(self.driver).move_to_element(self.driver.find_element(
                    By.CLASS_NAME, Config.NEXT_PAGE_BUTTON)).click().perform()
                return True
            else:
                # Button is disabled, return False to break out of the loop
                print("Last page reached. Stopping.")
                return False

        except ElementClickInterceptedException as e:
            logger.error(f"Element click intercepted: {e}")
            return False

        except Exception as e:
            logger.error(f"Error clicking next page button: {e}")
            return False

    def wait_for_next_page(self):
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, Config.CHAPTER_CARDS))
        )

    def wait_for_chapter_cards(self):
        try:
            # Wait for the chapter cards to load and be visible
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, Config.CHAPTER_CARDS))
            )
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_all_elements_located(
                    (By.CLASS_NAME, Config.CHAPTER_CARDS))
            )
        except NoSuchElementException as e:
            logger.error(f"No such element exception for chapter cards: {e}")
            raise
        except Exception as e:
            logger.error(f"Error while waiting for chapter cards: {e}")
            raise

    def wait_until_page_loaded(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, Config.PAGE_WRAP))
            )
        except Exception as e:
            logger.error(f"Error waiting for page to load: {e}")
            raise

    def wait_until_image_loaded(self):
        max_retries = 3
        retries = 0

        while retries < max_retries:
            try:
                img_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, Config.IMG))
                )
                current_img_src = img_element.get_attribute(Config.SRC)

                if current_img_src == self.last_loaded_img_src:
                    raise StaleElementReferenceException(
                        "Img source did not change from last time")

                self.last_loaded_img_src = current_img_src
                return  # Break out of the loop if successful

            except StaleElementReferenceException as stale_exception:
                logger.error(f"Stale element reference: {stale_exception}")
                # Refresh the entire page
                self.driver.refresh()

            except TimeoutException as timeout_exception:
                logger.error(
                    f"Timeout waiting for image to load: {timeout_exception}")

            retries += 1

        # If the loop completes without a successful attempt, raise an exception
        raise StaleElementReferenceException(
            "Max retries reached, unable to load image")

    def dismiss_popup_if_present(self):
        try:
            # Check if the popup is present
            # Replace 'popup-class-name' with the actual class name
            popup = self.driver.find_element(By.CLASS_NAME, Config.POP_UP)

            # Find all buttons in the popup
            buttons = popup.find_elements(By.TAG_NAME, 'button')

            # Filter the button with text "Continue" and click it
            continue_button = next(
                (button for button in buttons if 'Continue' in button.text), None)
            if continue_button:
                continue_button.click()
        except NoSuchElementException:
            pass  # No popup found, continue with the normal flow

    def check_element_exists(self, max_retries=3):
        try:

            retries = 0

            while retries < max_retries:
                try:
                    # Wait for the page to load
                    self.wait_until_page_loaded()

                    # Check if the manga image is present
                    manga_image = self.driver.find_elements(
                        By.CLASS_NAME, Config.MANGA_IMAGE)

                    if manga_image:

                        return Config.MANGA_IMAGE

                    # Check if the long manga image is present
                    long_manga_image = self.driver.find_elements(
                        By.CLASS_NAME, Config.LONG_MANGA_IMAGE)

                    if long_manga_image:

                        return Config.LONG_MANGA_IMAGE

                    retries += 1

                except TimeoutException:
                    # Handle timeout exception, e.g., log an error message
                    print("Timeout waiting for page to load.")
                    retries += 1

            print("Element not found after maximum retries.")
            return None

        except NoSuchElementException as e:
            logger.error(f"Error while checking if element exists: {e}")
            raise

    def reset_driver(self, img_data):
        try:
            # Close the current window
            self.driver.quit()
            # Re-initialize the driver and update the class attribute
            self.driver = self.setup_driver()
            # Navigate to the image URL
            self.driver.get(img_data)
            # Re-navigate to the chapter page (add your navigation logic here)
            # Example: self.driver.get("https://example.com/chapter")
        except Exception as e:
            logger.error(f"Error resetting driver: {e}")
