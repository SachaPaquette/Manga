from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException
from Config.config import Config
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
            
    def is_button_clickable(self, button):
        """
        Check if a button is clickable by verifying its class attribute and other conditions.

        Args:
            button (WebElement): The button element.

        Returns:
            bool: True if the button is clickable, False otherwise.
        """
        try:
            if 'disabled' in button.get_attribute('class') or button.value_of_css_property('pointer-events') == 'none' or button.get_attribute('aria-disabled') == 'true':
                return False
            
            return True
        
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

        except NoSuchElementException:
            # Next page button not found (last page reached)
            print("Next page button not found")
            return False

        except ElementClickInterceptedException as e:
            logger.error(f"Element click intercepted: {e}")
            return False

        except Exception as e:
            logger.error(f"Error clicking next page button: {e}")
            print(e)
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