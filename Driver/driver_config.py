from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import random
from Config.config import Config
import random
from Config.config import Config

def driver_setup():
    # Set up the driver options
    options = Options()
    # Keep the browser open after the script finishes executing (for debugging)
    options.add_experimental_option('detach', True)
    # Run in headless mode (without opening a browser window)
    options.add_argument('--headless')
    # Disable logging (1: INFO, 2: WARNING, 3: ERROR)
    options.add_argument("--log-level=3")
    # Set a random user agent
    options.add_argument(f"user-agent={random.choice(Config.USER_AGENTS)}")
    # ChromeDriverManager will install the latest version of ChromeDriver
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    # put the browser in focus
    driver.switch_to.window(driver.current_window_handle)
    return driver
