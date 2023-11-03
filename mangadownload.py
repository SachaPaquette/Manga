# Description: This script downloads manga from mangadex.org and saves it to the local disk.
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
# Load environment variables from .env file
load_dotenv()

# Set up logging to a file
logger = setup_logging('manga_download', Config.MANGA_DOWNLOAD_LOG_PATH)


class WebInteractions:
    def __init__(self):
        self.driver = self.setup_driver()  # Initialize the WebDriver instance
        self.original_tab_handle = None  # Store the original tab handle
        self.last_loaded_img_src = None  # Store the last loaded image source

    def setup_driver(self, headless=True):
        # Set up and return the WebDriver instance
        options = webdriver.ChromeOptions()

        if headless:
            options.add_argument('--headless')
            pass
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
        if button_class == Config.DEACTIVATED_NEXT_PAGE_BUTTON:
            return False
        return True

    def click_next_page(self):
        try:
            next_page_button = WebDriverWait(self.driver, 10).until(
                # Wait for the next page button to load
                EC.presence_of_element_located(
                    (By.CLASS_NAME, Config.NEXT_PAGE_BUTTON))
            )

            if self.is_button_clickable(next_page_button):
                ActionChains(self.driver).move_to_element(
                    next_page_button).click().perform()  # Click the next page button
                return True
            else:
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


class FileOperations:
    failed_images = []  # Array to store the images that failed to save

    def __init__(self, web_interactions=None):
        self.web_interactions = web_interactions
        self.original_tab_handles = None
        self.last_processed_url = None
        self.unique_base64_data = set()

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

                if current_url == self.last_processed_url:
                    logger.warning(
                        f"Duplicate URL detected, but continuing with sub-div {index + 1}")

                # Update the last processed URL
                self.last_processed_url = driver.current_url
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
            web_interactions.wait_until_image_loaded()

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


class MangaDownloader:

    def __init__(self, web_interactions=None):
        # Initialize the WebDriver instance, save path and logger
        self.web_interactions = web_interactions
        self.file_operations = FileOperations()
        self.save_path = os.getenv("SAVE_PATH")

    def fetch_chapters(self, link):
        logger.info(f"Fetching chapters for link: {link}")
        self.web_interactions.driver.get(link)  # Navigate to the link
        print("Fetching chapters...")

        try:
            self.web_interactions.wait_for_chapter_cards()
            time.sleep(3)  # Wait for the page to load

            # Check if there are chapters on the page
            chapter_cards = self.web_interactions.driver.find_elements(
                by=By.CLASS_NAME, value=Config.CHAPTER_CARDS)

            # Loop while there are still chapters to fetch
            chapters_array, first_chapter_number = self.process_chapter_cards(
                chapter_cards)
            while self.web_interactions.click_next_page():  # Click the next page button
                print("Waiting for next page to load...")
                self.web_interactions.wait_for_next_page()  # Wait for the next page to load
                chapter_cards = self.web_interactions.driver.find_elements(
                    by=By.CLASS_NAME, value=Config.CHAPTER_CARDS)  # Find all the chapter cards on the page
                # Process the chapter cards and append the results to the array
                chapters_array += self.process_chapter_cards(chapter_cards)[0]

        except Exception as e:
            logger.error(f"Error fetching chapters: {e}")
            raise
        finally:
            return chapters_array

    def process_chapter_cards(self, chapter_cards):
        chapters_array = []
        first_chapter_number = None
        for chapter in chapter_cards:
            try:
                # Extract the chapter info from the chapter card
                chapter_info = self.extract_chapter_info(chapter)

                if chapter_info:
                    print(
                        f"Fetched: {chapter_info['chapter_number']}, {chapter_info['chapter_name']}")
                    # Append the chapter info to the array
                    chapters_array.append(chapter_info)
                    # Get the chapter number of the first chapter
                    if first_chapter_number is None:
                        first_chapter_number = chapter_info['chapter_number']
            except NoSuchElementException as e:
                logger.error(f"Error while fetching chapter: {e}")
        return chapters_array, first_chapter_number

    def unsupported_website(self, link):
        # check if there is mangaplus in the link
        # mangaplus is not supported since the website layout is too different
        if "mangaplus" in link:
            return None
        else:
            return link

    def find_chapter_number(self, chapter):
        try:
            nested_divs = chapter.find_elements(
                by=By.TAG_NAME, value=Config.DIV)
            for nested_div in nested_divs:
                chapter_number = nested_div.find_element(
                    by=By.CLASS_NAME, value=Config.CHAPTER_NUMBER)

                return chapter_number
        except NoSuchElementException:
            pass

    def find_chapter_link(self, chapter):
        try:
            chapter_link_elements = chapter.find_elements(
                by=By.CLASS_NAME, value=Config.CHAPTER_LINK)
            flag_img_elements = [link.find_element(by=By.TAG_NAME, value=Config.IMG).get_attribute(
                'src') for link in chapter_link_elements]
            return chapter_link_elements, flag_img_elements
        except NoSuchElementException:
            return None, None
        except Exception as e:
            print(f"Error finding chapter link: {e}")
            raise

    def extract_chapter_info(self, chapter):
        chapter_number = self.find_chapter_number(chapter)
        if not chapter_number:
            return None

        chapter_link_elements, flag_img_elements = self.find_chapter_link(
            chapter)
        # Remove the loop since chapter_link_elements and flag_img_elements are lists
        if not chapter_link_elements:
            return None

        for chapter_link, flag_img in zip(chapter_link_elements, flag_img_elements):
            if flag_img == Config.UK_FLAG:
                # split the text into a list of strings and get the first element
                chapter_name = chapter_link.text.split('\n')[0]
                link = chapter_link.find_element(
                    by=By.TAG_NAME, value=Config.HYPERLINK).get_attribute(Config.HREF)

                # check if the website is supported
                link = self.unsupported_website(link)

                # remove leading and trailing spaces
                manga_chapter = chapter_number.text.strip()
                chapter_info = {
                    'chapter_number': manga_chapter,
                    'chapter_name': chapter_name,
                    'chapter_link': link if link else None,
                }
                return chapter_info

        return None

    def extract_chapter_id(self, page_url):
        # Split the URL by the forward slash, e.g. https://mangadex.org/chapter/12345/1 -> ['https:', '', 'mangadex.org', 'chapter', '12345', '1'] -> we want the chapter ID which is the 5th element
        parts = page_url.split("/")
        try:
            index = parts.index("chapter")  # Get the index of the chapter ID
            if index + 1 < len(parts):
                return parts[index + 1]  # Return the chapter ID
        except ValueError:
            pass
        return None

    def download_images_from_chapter(self, chapter_link, series_name, chapter_number):
        try:
            page_number = 1  # Initialize the page number
            long_screenshot_taken = False  # Initialize the long screenshot flag
            if chapter_link is None:
                logger.error("Chapter link is None. Exiting.")
                return

            # Sanitize the folder name (remove characters not allowed in a folder name)
            sanitized_folder_name = self.file_operations.sanitize_folder_name(
                series_name)
            save_path = os.path.join(
                self.save_path, sanitized_folder_name, str(chapter_number))

            # Check if the folder for the chapter already exists, if so, exit
            if os.path.exists(save_path):
                logger.warning(
                    f"Folder for {chapter_number} already exists. Exiting.")
                return
            else:
                # Navigate to the chapter link
                self.web_interactions.driver.get(chapter_link)
                time.sleep(3)  # Wait for the page to load
                print("Waiting for chapter to load...")
                previous_chapter_id = self.extract_chapter_id(
                    chapter_link)  # Get the initial chapter ID from the URL
                time.sleep(2)
                # Check if it's a long manga
                is_long_manga = Config.LONG_MANGA_IMAGE in self.web_interactions.check_element_exists()
                time.sleep(2)
                while True:
                    try:
                        if previous_chapter_id is None:
                            logger.error(
                                "Previous chapter ID is None. Exiting.")
                            return

                        if previous_chapter_id != self.extract_chapter_id(self.web_interactions.driver.current_url) and not is_long_manga:
                            logger.info("Chapter completed.")
                            return

                        if Config.LONG_MANGA_IMAGE in self.web_interactions.check_element_exists() and not long_screenshot_taken:
                            long_screenshot_taken = True

                            # Process long manga differently
                            self.file_operations.save_long_screenshot(
                                self.web_interactions.driver, self.save_path, series_name, chapter_number, None)
                            # Increment the page number for long manga
                            break

                        elif not is_long_manga:
                            # Press the right arrow key to go to the next page for small manga
                            self.process_page(
                                page_number, previous_chapter_id, series_name, chapter_number)

                    except StopIteration:
                        break
                    finally:
                        if not is_long_manga:
                            page_number += 1  # Increment the page number for small manga

        except Exception as e:
            logger.critical(f"Critical error: {e}")
        finally:
            pass

    def process_page(self, page_number, previous_chapter_id, series_name, chapter_number):
        # Wait for the pages wrap element to load
        self.web_interactions.wait_until_page_loaded()
        before_url = self.web_interactions.driver.current_url

        # Check if it's a long manga
        config = self.web_interactions.check_element_exists()

        if config == Config.MANGA_IMAGE:
            # Save a screenshot of the page
            self.file_operations.save_screenshot(
                self.web_interactions.driver, self.save_path, series_name, chapter_number, page_number)
            # For small manga, proceed with arrow key press
            ActionChains(self.web_interactions.driver).send_keys(
                Keys.ARROW_RIGHT).perform()
        elif config == None:
            print("No manga image found")
            return
        else:
            print("Error")
            return
        # Get the current chapter ID after the arrow key press
        current_chapter_id = self.extract_chapter_id(
            self.web_interactions.driver.current_url)

        # Check if the chapter ID has changed (i.e., the chapter has ended)
        if current_chapter_id != previous_chapter_id:
            logger.info("Chapter completed.")
            self.file_operations.delete_last_page(
                self.save_path, series_name, chapter_number, page_number)
            raise StopIteration

        # Check if the URL has changed after pressing the right arrow key
        if self.web_interactions.driver.current_url == before_url:
            logger.error(
                "URL did not change after pressing the right arrow key. Stopping.")
            # Popup is present on the page
            self.web_interactions.dismiss_popup_if_present()
            raise StopIteration

    def search_and_select_manga(self):
        # Ask the user to enter the name of the manga
        name = input("Enter the name of the manga: ")
        mangas = find_mangas(name)  # Search for the manga

        if mangas:
            print("Search results:")
            for i, manga in enumerate(mangas):
                print(f"{i + 1}. {manga['title']}")  # Print the manga titles

            selected_index = input(
                "Enter the number of the manga you want to download (or '0' to exit): ")  # Ask the user to select a manga

            if selected_index == '0':
                print("Exiting.")
                return (), ""  # Return an empty tuple and an empty string

            if selected_index.isdigit() and 0 <= int(selected_index) <= len(mangas):
                # Get the selected manga
                selected_manga = mangas[int(selected_index) - 1]
                print(
                    f"You selected: {selected_manga['title']}")
                # Fetch all the chapters for the selected manga
                all_chapters = self.fetch_chapters(selected_manga['link'])
                print("Done.")
                # Return the chapters and the name of the manga
                return all_chapters, selected_manga['title']
            else:
                # make the user re-enter the number
                print("Invalid number. Please enter a valid number.")
                return self.search_and_select_manga()
        else:
            print("No manga found. Please try again\n")

            # make the user re-enter the name of the manga
            return self.search_and_select_manga()


if __name__ == "__main__":
    try:

        # Instantiate WebInteractions, FileOperations, and MangaDownloader
        web_interactions = WebInteractions()
        file_operations = FileOperations(web_interactions)
        manga_downloader = MangaDownloader(web_interactions)
        # Search and select a manga
        chapters, series_name = manga_downloader.search_and_select_manga()

        if chapters and series_name:
            # Once you have the chapters, you can loop through them and download images
            for chapter in chapters:
                print(
                    f"{chapter['chapter_number']}, {chapter['chapter_name']}")
                manga_downloader.download_images_from_chapter(
                    chapter['chapter_link'], series_name, chapter['chapter_number']
                )  # Download images from the chapter

        # Clean up resources
        web_interactions.cleanup()

    except KeyboardInterrupt as e:
        print("\nQuitting...")
