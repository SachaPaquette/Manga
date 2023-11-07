import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import  NoSuchElementException
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
        # Initialize the WebDriver instance, save path and logger
        self.web_interactions = web_interactions if web_interactions else WebInteractions()
        self.file_operations = file_operations if file_operations else FileOperations(self.web_interactions)
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
                                "Previous chapter ID is None. Exiting.") # Error handling
                            return

                        if previous_chapter_id != self.extract_chapter_id(self.web_interactions.driver.current_url) and not is_long_manga:
                            logger.info("Chapter completed.") # Error handling
                            return

                        if Config.LONG_MANGA_IMAGE in self.web_interactions.check_element_exists() and not long_screenshot_taken:
                            long_screenshot_taken = True # Set the long screenshot boolean variable to True to prevent taking another long screenshot

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
            self.file_operations.take_long_screenshot(
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