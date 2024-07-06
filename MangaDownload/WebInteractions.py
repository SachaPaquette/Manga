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
from Config.config import Config
import re
import json
import base64
import hashlib
from Config.logs_config import setup_logging
from Driver.driver_config import driver_setup
logger = setup_logging('manga_download', Config.MANGA_DOWNLOAD_LOG_PATH)

from enum import Enum

class WaitCondition(Enum):
    FIRST_PAGE = 1
    PAGE_WRAP = 2
    
class WebInteractions:
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        # Create a new instance if one doesn't already exist
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'driver'):
            return  # Return if instance already initialized

        self.driver = driver_setup()  # Initialize the WebDriver instance
        self.original_tab_handle = None  # Store the original tab handle
        self.last_loaded_img_src = None  # Store the last loaded image source

    def cleanup(self):
        try:
            self.driver.close()  # Close the current tab
            print("Resources cleaned up.")
        except NoSuchWindowException:
            print("No such window exception while cleaning up resources.")
        except InvalidSessionIdException:
            print("Invalid session ID exception while cleaning up resources.")
        except WebDriverException:
            print("Web driver exception while cleaning up resources.")
        except Exception as e:
            print(f"Error while cleaning up resources: {e}")
            
    def is_button_clickable(self, button):
        # current button layout is button > span > svg - we currently have the svg element
        span_element = button.find_element(
            By.XPATH, '..')  # Get the span element
        button_element = span_element.find_element(
            By.XPATH, '..')  # Get the button element
        button_class = button_element.get_attribute('class')
        # Check if the button is disabled
        if 'disabled' in button_class:
            # Button is disabled, return False to break out of the loop
            return False
        # Button is enabled, return True
        return True
    def press_right_arrow_key(self):
        ActionChains(self.driver).send_keys(
                    Keys.ARROW_RIGHT).perform()

    def click_next_page(self):
        try:
            # Find the next page button
            next_page_button = self.driver.find_element(By.CLASS_NAME, Config.NEXT_PAGE_BUTTON)
            
            # Check if the next page button exists on the page
            if next_page_button:
                # Check if the next page button is clickable
                if self.is_button_clickable(next_page_button):
                    # Click the next page button using ActionChains
                    ActionChains(self.driver).move_to_element(next_page_button).click().perform()
                    return True
                else:
                    # Button is disabled, print message and return False
                    print("Last page reached. Stopping.")
                    return False
            else:
                # Next page button not found, print message and return False
                print("Next page button not found.")
                return False

        except NoSuchElementException:
            # Handle element not found exception
            logger.error("Next page button not found")
            return False

        except ElementClickInterceptedException as e:
            # Handle click interception exception
            logger.error(f"Element click intercepted: {e}")
            return False

        except Exception as e:
            # Handle other unexpected exceptions
            logger.error(f"Error clicking next page button: {e}")
            return False

    def wait_until(self, condition, timeout=10, multiple=False):
        if multiple:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located(
                    condition
                )
            )
        else:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    condition
                )
            )
            
    
    def wait_for_next_page(self):
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, Config.CHAPTER_CARDS))
        )

    def wait_for_chapter_cards(self):
        try:
            while True:
                # Wait until one chapter card is loaded
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, Config.CHAPTER_CARDS))
                )       
                break
        except TimeoutException:
            logger.error("Timed out waiting for chapter cards to load")
            raise
        except NoSuchElementException as e:
            logger.error(f"No such element exception for chapter cards: {e}")
            raise
        except Exception as e:
            logger.error(f"Error while waiting for chapter cards: {e}")
            raise

    def wait_until_page_loaded(self, wait_condition):
        """
        Wait until a specific element is loaded on the page based on the given wait condition.

        Args:
            wait_condition (WaitCondition): The condition to wait for after navigation.

        Raises:
            TimeoutException: If the element is not loaded within the specified timeout.
        """
        try:
            if wait_condition == WaitCondition.FIRST_PAGE.value:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'chapter-grid.flex-grow'))
                )
            elif wait_condition == WaitCondition.PAGE_WRAP.value:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, Config.PAGE_WRAP))
                )
        except TimeoutException:
            logger.error("Timed out waiting for page to load")

    def wait_until_image_loaded(self):
        """
        Waits until the manga image is fully loaded on the page.
        If the image is not loaded after a certain number of retries, raises a StaleElementReferenceException.
        """
        max_retries = 6
        retries = 0

        while retries < max_retries:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, Config.MANGA_IMAGE))
                )
                
                # Get all img elements within the located element
                img_elements = element.find_elements(By.TAG_NAME, 'img')

                for img_element in img_elements:
                    # Get the image source
                    img_src = img_element.get_attribute('src')

                    if img_src and (img_src.startswith('blob:') or img_src.startswith('data:image')):
                        # Image source is not empty and starts with 'data:image', indicating a fully loaded image
                        return img_src

            except StaleElementReferenceException as stale_exception:
                logger.error(f"Stale element reference: {stale_exception}")
                # Refresh the entire page
                self.driver.refresh()

            except TimeoutException as timeout_exception:
                logger.error(f"Timeout waiting for image to load: {timeout_exception}")

            time.sleep(1.5)
            retries += 1

        # If the loop completes without a successful attempt, raise an exception
        raise StaleElementReferenceException("Max retries reached, unable to load image")



    def dismiss_popup_if_present(self):
        try:
            # Check if the popup is present
            popup = self.find_single_element(
                By.CLASS_NAME, Config.POP_UP, None)

            # Find all buttons in the popup
            buttons = self.find_multiple_elements(
                By.TAG_NAME, 'button', popup)

            # Filter the button with text "Continue" and click it
            continue_button = next(
                (button for button in buttons if 'Continue' in button.text), None)
            if continue_button:
                continue_button.click()
        except NoSuchElementException:
            pass  # No popup found, continue with the normal flow

    def check_element_exists(self, max_retries=6):
        try:
            retries = 0

            while retries < max_retries:
                try:
                    # Wait for the page to load
                    self.wait_until_page_loaded(2)

                    # Check if the manga image is present
                    manga_images = self.find_multiple_elements(By.CLASS_NAME, Config.MANGA_IMAGE, None)
                    long_manga_images = self.find_multiple_elements(By.CLASS_NAME, Config.LONG_MANGA_IMAGE, None)

                    if manga_images:
                        return Config.MANGA_IMAGE
                    elif long_manga_images:
                        return Config.LONG_MANGA_IMAGE
                    else:
                        raise NoSuchElementException("Manga image not found")

                    

                except TimeoutException:
                    # Handle timeout exception, e.g., log an error message
                    print("Timeout waiting for page to load.")
                    time.sleep(2)
                    retries += 1

            print("Element not found after maximum retries.")
            return False  # Element not found

        except NoSuchElementException as e:
            logger.error(f"Error while checking if element exists: {e}")
            

    def naviguate(self, url, wait_condition=None):
            """
            Navigates to the specified URL using the Selenium WebDriver instance associated with this object.

            Args:
                url (str): The URL to navigate to.

            Raises:
                Exception: If an error occurs while navigating to the specified URL.
            """
            try:
                self.driver.get(url)
                if wait_condition:
                    self.wait_until_page_loaded(wait_condition)   
            except Exception as e:
                logger.error(f"Error while navigating to {url}: {e}")
                
    def find_multiple_elements(self, type_name, value, element=None):
            """
            Finds multiple elements on the page using the specified search criteria.

            Args:
                type_name (str): The type of search to perform (e.g., "class name", "tag name", etc.).
                value (str): The value to search for.
                element (WebElement): The element to search within (optional).

            Returns:
                A list of WebElements that match the specified search criteria.
            """
            by_type = getattr(By, type_name.replace(' ', '_').upper())

            if element:
                return element.find_elements(by=by_type, value=value)
            else:
                return self.driver.find_elements(by=by_type, value=value)

    def find_single_element(self, type_name, value, element=None):
        """
        Finds a single element on the page using the specified search criteria.

        Args:
            type_name (str): The type of search to perform (e.g., "class name", "tag name", etc.).
            value (str): The value to search for.
            element (WebElement): The element to search within (optional).

        Returns:
            The WebElement that matches the specified search criteria.
        """
        by_type = getattr(By, type_name.replace(' ', '_').upper())

        if element:
            return element.find_element(by=by_type, value=value)
        else:
            return self.driver.find_element(by=by_type, value=value)
        
    def wait_until_element_loaded(self, type_name, value, timeout=10):
        """
        Waits until the specified element is loaded on the page.

        Args:
            type_name (str): The type of element to search for (e.g., 'id', 'class_name', 'xpath').
            value (str): The value associated with the type of element.
            timeout (int): The maximum time to wait for the element to be loaded.
        """
        by_type = getattr(By, type_name.replace(' ', '_').upper())
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by_type, value))
        )