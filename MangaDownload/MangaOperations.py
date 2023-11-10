import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import  NoSuchElementException, TimeoutException
from dotenv import load_dotenv
import time
from database import find_mangas
from Config.config import Config
from Config.logs_config import setup_logging
from MangaDownload.FileOperations import FileOperations
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.WebInteractions import logger

class MangaDownloader:

    def __init__(self, web_interactions=None, file_operations=None):
        """
        Initializes a MangaOperations object with the given WebInteractions and FileOperations instances.

        :param web_interactions: A WebInteractions instance to use for web interactions. If None, a new instance will be created.
        :type web_interactions: WebInteractions or None
        :param file_operations: A FileOperations instance to use for file operations. If None, a new instance will be created.
        :type file_operations: FileOperations or None
        """
        # Initialize the WebDriver instance, save path and logger
        self.web_interactions = web_interactions if web_interactions else WebInteractions()
        self.file_operations = file_operations if file_operations else FileOperations(self.web_interactions)
        self.save_path = os.getenv("SAVE_PATH")



 
    def fetch_chapters(self, link):
        """
        Fetches all the chapters for a given manga link.

        :param link: The link to the manga.
        :type link: str
        :return: A list of chapter objects.
        :return type: list
        """
        logger.info(f"Fetching chapters for link: {link}")
        self.web_interactions.naviguate(link)  # Navigate to the link
        print("Fetching chapters...")

        try:
            self.web_interactions.wait_for_chapter_cards()
            time.sleep(3)  # Wait for the page to load

            # Check if there are chapters on the page
            chapter_cards = self.web_interactions.driver.find_elements(
                by=By.CLASS_NAME, value=Config.CHAPTER_CARDS)

            # Loop while there are still chapters to fetch
            chapters_array, _ = self.process_chapter_cards(
                chapter_cards)
            while True:  # Change the loop condition
                print("Waiting for next page to load...")
                if not self.web_interactions.click_next_page():  # Check the return value
                    print("No next page. Stopping.")
                    break

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
            """
            Extracts chapter information from the given chapter cards and returns an array of chapter info objects
            along with the number of the first chapter.

            Args:
                chapter_cards (list): A list of chapter cards to extract information from.

            Returns:
                tuple: A tuple containing the array of chapter info objects and the number of the first chapter.
            """
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
            """
            Checks if the given link is from the mangaplus website, which is not supported due to its different layout.

            Args:
                link (str): The link to check.

            Returns:
                str or None: The original link if it is not from mangaplus, or None if it is.
            """
            if "mangaplus" in link:
                return None
            else:
                return link

    def find_chapter_number(self, chapter):
        """
        This function finds the chapter number from a given chapter element.

        Parameters:
        chapter (WebElement): A WebElement representing a chapter.

        Returns:
        chapter_number (WebElement): A WebElement representing the chapter number.
        """

        try:
            # Find all div elements within the chapter element
            nested_divs = chapter.find_elements(by=By.TAG_NAME, value=Config.DIV)

            # Iterate over each div element
            for nested_div in nested_divs:
                # Find the chapter number within the div element
                chapter_number = nested_div.find_element(by=By.CLASS_NAME, value=Config.CHAPTER_NUMBER)

                # Return the chapter number
                return chapter_number

        except NoSuchElementException:
            # If the chapter number is not found, do nothing and exit the function
            pass

    def find_chapter_link(self, chapter):
            """
            Finds the chapter link elements and flag image elements for a given chapter.

            Args:
                chapter: The chapter element to search for links and flag images.

            Returns:
                A tuple containing the chapter link elements and flag image elements, or None if not found.
            """
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
            """
            Extracts chapter information from the given chapter element.

            Args:
                chapter: The chapter element to extract information from.

            Returns:
                A dictionary containing the extracted chapter information, including the chapter number,
                chapter name, and chapter link. Returns None if the chapter information could not be extracted.
            """
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
            """
            Extracts the chapter ID from a given page URL.

            Args:
                page_url (str): The URL of the page containing the chapter ID.

            Returns:
                str: The chapter ID extracted from the URL, or None if the URL does not contain a chapter ID.
            """
            # Split the URL by the forward slash, e.g. https://mangadex.org/chapter/12345/1 -> ['https:', '', 'mangadex.org', 'chapter', '12345', '1'] -> we want the chapter ID which is the 5th element
            parts = page_url.split("/")
            try:
                index = parts.index("chapter")  # Get the index of the chapter ID
                if index + 1 < len(parts):
                    return parts[index + 1]  # Return the chapter ID
            except ValueError:
                pass
            return None


    def check_value_none(self, value):
        try:
            if value is None:
                logger.error(f"{value} is None. Exiting.")
                return 
        except Exception as e:
            logger.error(f"Error checking if value is None: {e}")
            raise
    
    def create_folder(self, series_name, chapter_number):
        try:
            # Sanitize the folder name (remove characters not allowed in a folder name)
            sanitized_folder_name = self.file_operations.sanitize_folder_name(
                series_name)
            save_path = os.path.join(
                self.save_path, sanitized_folder_name, str(chapter_number))
            return save_path
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise
        
    def check_if_file_exists(self, save_path, chapter_number):
        # Check if the folder for the chapter already exists, if so, exit
        if os.path.exists(save_path):
            logger.warning(
                f"Folder for {chapter_number} already exists. Exiting.")
            
    def long_manga(self, long_screenshot_taken, series_name, chapter_number):
        long_screenshot_taken = True # Set the long screenshot boolean variable to True to prevent taking another long screenshot

        # Process long manga differently
        self.file_operations.save_long_screenshot(
        self.web_interactions.driver, self.save_path, series_name, chapter_number, None)
        return long_screenshot_taken
    
    def download_images_from_chapter(self, chapter_link, series_name, chapter_number):
        try:
            save_path = self.prepare_save_path(series_name, chapter_number)
            if os.path.exists(save_path):
                logger.warning(
                    f"Folder for {chapter_number} already exists. Exiting.")
                return

            self.navigate_to_chapter(chapter_link)
            previous_chapter_id = self.extract_chapter_id(chapter_link)
            is_long_manga = Config.LONG_MANGA_IMAGE in self.web_interactions.check_element_exists()

            self.process_chapter(is_long_manga, previous_chapter_id, series_name, chapter_number)

        except NoSuchElementException as e:
            logger.error(f"Element not found: {e}")
        except TimeoutException as e:
            logger.error(f"Loading took too much time: {e}")
        except Exception as e:
            logger.critical(f"Critical error: {e}")
        finally:
            pass

    def prepare_save_path(self, series_name, chapter_number):
        sanitized_folder_name = self.file_operations.sanitize_folder_name(series_name)
        return os.path.join(self.save_path, sanitized_folder_name, str(chapter_number))

    def navigate_to_chapter(self, chapter_link):
        """
        Navigates to the given chapter link and waits for the page to load.

        Args:
            chapter_link (str): The URL of the chapter to navigate to.
        """
        self.web_interactions.naviguate(chapter_link)
        time.sleep(3)  # Wait for the page to load
        self.web_interactions.wait_until_element_loaded(By.CSS_SELECTOR, 'body')

    def process_chapter(self, is_long_manga, previous_chapter_id, series_name, chapter_number):
        # Initialize the page number and long screenshot taken variables
        page_number = 1
        long_screenshot_taken = False

        while True:
            try:
                if previous_chapter_id is None:
                    logger.error("Previous chapter ID is None. Exiting.")
                    return

                if previous_chapter_id != self.extract_chapter_id(self.web_interactions.driver.current_url) and not is_long_manga:
                    logger.info("Chapter completed.")
                    return

                if Config.LONG_MANGA_IMAGE in self.web_interactions.check_element_exists() and not long_screenshot_taken:
                    long_screenshot_taken = True
                    self.file_operations.save_long_screenshot(
                        self.web_interactions.driver, self.save_path, series_name, chapter_number, None)
                    break

                elif not is_long_manga:
                    element_exists_result = self.web_interactions.check_element_exists()

                    if element_exists_result:
                        self.process_page(
                            page_number, previous_chapter_id, series_name, chapter_number)
                    else:
                        logger.warning("Element does not exist.")
                        break

            except StopIteration:
                break
            finally:
                if not is_long_manga:
                    # Increment the page number
                    page_number += 1


    def process_page(self, page_number, previous_chapter_id, series_name, chapter_number):
        # Wait for the pages wrap element to load
        self.web_interactions.wait_until_page_loaded()
        # Get the URL before pressing the right arrow key
        before_url = self.web_interactions.driver.current_url

        # Check if it's a long manga
        config = self.web_interactions.check_element_exists()

        error_count = 0  # Initialize error count
        max_error_count = 3  # Set a maximum number of consecutive errors allowed

        while True:
            if config == Config.MANGA_IMAGE:
                img_src = self.web_interactions.wait_until_image_loaded()
                # Save a screenshot of the page
                self.file_operations.take_screenshot(
                    self.web_interactions.driver, self.save_path, series_name, chapter_number, page_number, img_src)
                # For small manga, proceed with arrow key press
                self.web_interactions.press_right_arrow_key()
            elif config == None:
                print("No manga image found")
                return
            else:
                print("Error")
                error_count += 1  # Increment error count
                if error_count >= max_error_count:
                    print(f"Exceeded maximum consecutive errors ({max_error_count}). Exiting.")
                    raise StopIteration
                continue

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
            else:
                break

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