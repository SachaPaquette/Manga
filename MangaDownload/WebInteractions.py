import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from Config.config import Config
from Config.logs_config import setup_logging
from Driver.driver_config import driver_setup
from enum import Enum
from threading import Lock

logger = setup_logging('manga_download', Config.MANGA_DOWNLOAD_LOG_PATH)

class WaitCondition(Enum):
    FIRST_PAGE = 1
    PAGE_WRAP = 2

class WebInteractions:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'driver'):
            return  # Prevent re-initialization

        self.driver = driver_setup()
        self.original_tab_handle = None
        self.last_loaded_img_src = None

    def is_button_clickable(self, button):
        """
        Check if a button is clickable.

        Args:
            button (WebElement): The button element.

        Returns:
            bool: True if the button is clickable, False otherwise.
        """
        try:
            class_attr = button.get_attribute('class') or ''
            aria_disabled = button.get_attribute('aria-disabled') or 'false'

            return all([
                'disabled' not in class_attr,
                button.value_of_css_property('pointer-events') != 'none',
                aria_disabled.lower() != 'true',
            ])
        except Exception as e:
            logger.error(f"Error checking button clickable status: {e}")
            return False

    def click_next_page(self):
        """
        Click the next page button using JavaScript if it exists and is clickable.

        Returns:
        bool: True if the button is clicked successfully, False otherwise.
        """
        try:
            # Find the parent element of the next page button
            next_page_button_parent = self.driver.find_element(By.CLASS_NAME, Config.NEXT_PAGE_BUTTON).find_element(By.XPATH, '../..')

            if next_page_button_parent and self.is_button_clickable(next_page_button_parent):
                self.driver.execute_script("""
                    var event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    arguments[0].dispatchEvent(event);
                """, next_page_button_parent)
                return True
            return False

        except ElementClickInterceptedException:
            logger.error("Element click intercepted")
            return False
        except NoSuchElementException:
            logger.error("Next page button not found")
            return False
        except Exception as e:
            logger.error(f"Error clicking next page button: {e}")
            return False

    def wait_until(self, condition, timeout=10, multiple=False):
        try:
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
        except TimeoutException:
            logger.error("Timed out waiting for element to load")
        except Exception as e:
            logger.error(f"Error while waiting for element to load: {e}")


    def wait_until_page_loaded(self, wait_condition, timeout=10):
        """
        Wait until a specific element is loaded on the page based on the given wait condition.

        Args:
            wait_condition (WaitCondition): The condition to wait for after navigation.

        Raises:
            TimeoutException: If the element is not loaded within the specified timeout.
        """
        try:
            if wait_condition == WaitCondition.FIRST_PAGE.value:
                self.wait_until((By.CLASS_NAME, 'chapter-grid.flex-grow'), timeout, False)
            elif wait_condition == WaitCondition.PAGE_WRAP.value:
                self.wait_until((By.CLASS_NAME, Config.PAGE_WRAP), timeout, False)
        except TimeoutException:
            logger.error("Timed out waiting for page to load")
        except Exception as e:
            logger.error(f"Error while waiting for page to load: {e}")

    def navigate(self, url, wait_condition=None):
        """
        Navigate to a URL and wait for a condition.

        Args:
            url (str): URL to navigate to.
            wait_condition (WaitCondition): Condition to wait for after navigation.
        """
        if not url or not isinstance(url, str):
            logger.error(f"Invalid URL provided: {url}")
            return False

        try:
            self.driver.get(url)
            if wait_condition:
                self.wait_until_page_loaded(wait_condition)
            return True
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False


    def wait_until_element_loaded(self, type_name, value, timeout=10):
        """
        Wait until a specific element is loaded.

        Args:
            type_name (str): Type of locator (e.g., 'id', 'class_name').
            value (str): Locator value.
            timeout (int): Maximum wait time in seconds.
        """
        by_type = getattr(By, type_name.upper())
        self.wait_for_element(by_type, value, timeout)

    def wait_for_element(self, by, value, timeout=10, multiple=False):
        """
        Wait for an element to appear on the page.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Locator value.
            timeout (int): Time to wait in seconds.
            multiple (bool): Wait for multiple elements if True.

        Returns:
            WebElement or list[WebElement]: Located element(s).
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            if multiple:
                elements = wait.until(EC.presence_of_all_elements_located((by, value)))
            else:
                elements = wait.until(EC.presence_of_element_located((by, value)))
            logger.info(f"Successfully located element(s) by {by} with value {value}")
            return elements
        except TimeoutException:
            logger.error(f"Timeout waiting for element by {by} with value {value}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error waiting for element by {by} with value {value}: {e}")
            return None
