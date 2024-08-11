import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import random
from Config.config import Config
from selenium.common.exceptions import WebDriverException

def check_chrome_installed():
    """
    Function to check if Google Chrome is installed on the user's system.
    """
    try:
        # Try to install ChromeDriver 
        ChromeDriverManager().install()
    except WebDriverException:
        # Chrome is not installed on the system
        print("Chrome is not installed on your system. Please install it and try again.")
        sys.exit()

def configure_browser_options(options, user_agents, crx_path):
    """
    Configures the browser options for automated testing.

    Args:
        options (Options): The browser options object.
        user_agents (list): List of user agents to choose from.
        crx_path (str): The path to the extension file.

    Returns:
        None
    """
    # Disable logging (1: INFO, 2: WARNING, 3: ERROR)
    options.add_argument("--log-level=3")
    # Disable the "DevTools listening on ws://
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # Disable the "Chrome is being controlled by automated test software" notification
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # Turn-off userAutomationExtension 
    options.add_experimental_option("useAutomationExtension", False)
    # Set a random user agent (pretend to be a real browser)
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    # Add the extension to the driver (for ad blocking)
    options.add_extension(crx_path)
    # Adding argument to disable the AutomationControlled flag
    options.add_argument("--disable-blink-features=AutomationControlled")

def driver_setup():
    """
    Set up and configure the web driver for automated browser testing.

    Returns:
        WebDriver: The configured web driver instance.
    Raises:
        Exception: If an error occurs during the driver setup process.
    """
    try:
        # Set up the driver options
        options = Options()
        # Run in headless mode (without opening a browser window)
        #options.add_argument('--headless')
        # Disable logging and configure other options
        configure_browser_options(options, Config.USER_AGENTS, Config.CRX_PATH)
        # Check if Chrome is installed
        check_chrome_installed()
        # ChromeDriverManager will install the latest version of ChromeDriver
        # Set up desired capabilities
        caps = DesiredCapabilities().CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        driver = webdriver.Chrome(service=Service(service=Service(check_chrome_installed()), options=options, desired_capabilities=caps))
        # Changing the property of the navigator value for webdriver to undefined
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        # Return the driver instance
        return driver
    except Exception as e:
        # Raise the exception
        raise e
