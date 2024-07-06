import json
import os
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import  NoSuchElementException, TimeoutException
from dotenv import load_dotenv
import time, datetime 
from Config.config import Config
from Config.logs_config import setup_logging
from MangaDownload.FileOperations import FileOperations
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.WebInteractions import logger
from MangaFetch.FetchOperations import fetch_and_process_manga_cards
from selenium.webdriver.support.ui import WebDriverWait

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
        self.added_chapter_numbers = set()  # Keep track of added chapter numbers
        self.chapter_number_list = []  # Keep track of chapter numbers
        self.previous_chapter_name = None  # Keep track of the previous chapter name
        # Configure the save path
        if os.getenv("SAVE_PATH") is not None:
            self.save_path = os.getenv("SAVE_PATH")
        else:
            print("SAVE_PATH environment variable not found.")
            self.save_path = Config.DEFAULT_SAVE_PATH
            print(f"Using default save path to save mangas: {self.save_path}")

    def print_chapter_info(self, chapter):
        """
        Print the chapter number and name.
        """
        print(f"{chapter['chapter_number']}, {chapter['chapter_name']}, {chapter['chapter_link']}")

 
    def fetch_chapters(self, link):
        """
        Fetches all the chapters for a given manga link.

        :param link: The link to the manga.
        :type link: str
        :return: A list of chapter objects.
        :rtype: list
        """
        # Navigate to the manga link
        self.web_interactions.naviguate(link, wait_condition=1)
        chapters_array = []

        try:
            self.web_interactions.wait_for_chapter_cards()
            chapters_array = self.collect_chapters()

            self.fill_missing_chapter_numbers(chapters_array)
        except Exception as e:
            logger.error(f"Error fetching chapters: {e}")
            raise

        return chapters_array if chapters_array else []

    def collect_chapters(self):
        """
        Collects chapters from the current and subsequent pages.

        :return: A list of chapter objects.
        :rtype: list
        """
        chapters_array = []

        while True:
            chapter_cards = self.web_interactions.driver.find_elements(By.CLASS_NAME, Config.CHAPTER_CARDS)
            chapters_array += self.process_chapter_cards(chapter_cards)

            if not self.web_interactions.click_next_page():
                break

            self.web_interactions.wait_until_page_loaded(1)

        return chapters_array

    def process_chapter_cards(self, chapter_cards):
        """
        Processes the chapter cards and extracts chapter information.

        :param chapter_cards: List of chapter card elements.
        :type chapter_cards: list
        :return: A list of chapter objects.
        :rtype: list
        """
        chapters = []
        for card in chapter_cards:
            # Extract chapter details from the card
            chapter = self.extract_chapter_info(card)
            chapters.append(chapter)
        return chapters

    def extract_chapter_info(self, card):
        """
        Extracts chapter information from a chapter card element.

        :param card: The chapter card element.
        :type card: WebElement
        :return: A dictionary with chapter information.
        :rtype: dict
        """
        # Placeholder for extracting chapter information
        # Implement the actual extraction logic based on the structure of chapter card elements
        return {
            'chapter_number': None,  # Replace with actual extraction logic
            # Add other fields as necessary
        }

    def fill_missing_chapter_numbers(self, chapters_array):
        """
        Fills missing chapter numbers in the chapters array.

        :param chapters_array: List of chapter objects.
        :type chapters_array: list
        """
        for i, chapter in enumerate(chapters_array):
            if chapter['chapter_number'] is None:
                if i > 0 and chapters_array[i - 1]['chapter_number'] is not None:
                    chapter['chapter_number'] = chapters_array[i - 1]['chapter_number'] - 1
                elif i < len(chapters_array) - 1 and chapters_array[i + 1]['chapter_number'] is not None:
                    chapter['chapter_number'] = chapters_array[i + 1]['chapter_number'] + 1
                else:
                    chapter['chapter_number'] = len(chapters_array) - i


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

        for chapter in chapter_cards:
            try:
                # Extract the chapter info from the chapter card
                chapter_info = self.extract_chapter_info(chapter)

                # Check if the chapter number has already been added
                if chapter_info and chapter_info["chapter_name"] != self.previous_chapter_name:
                    chapters_array.append(chapter_info)
                    #self.added_chapter_numbers.add(chapter_info["chapter_number"])
                    self.previous_chapter_name = chapter_info["chapter_name"]
            except NoSuchElementException as e:
                logger.error(f"Error while fetching chapter: {e}")
            except Exception as e:
                logger.error(f"Error processing chapter cards: {e}")
                continue
        return chapters_array



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


    def find_chapter_link(self, chapter):
        """
        Finds the chapter link elements and flag image elements for a given chapter.

        Args:
            chapter: The chapter element to search for links and flag images.

        Returns:
            A tuple (link element, link URL) corresponding to the English title, or None if not found.
        """
        try:
            # Find all chapter link elements within the chapter
            chapter_link_elements = chapter.find_elements(by=By.CLASS_NAME, value=Config.CHAPTER_LINK)
            
            for link in chapter_link_elements:
                try:
                    # Check if the link has an image element with title attribute 'English'
                    img_element = link.find_element(by=By.TAG_NAME, value=Config.IMG)
                    if img_element.get_attribute('title') == 'English':
                        links = link.find_element(by=By.TAG_NAME, value=Config.HYPERLINK).get_attribute(Config.HREF)
                        if links and self.unsupported_website(links):
                            return link, links
                except NoSuchElementException:
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"Error finding chapter link: {e}")
            return None


    def extract_chapter_number(self, chapter):
        try:            
            soup = BeautifulSoup(chapter.get_attribute('innerHTML'), 'html.parser')
            chapter_number = soup.find('span', class_='font-bold self-center whitespace-nowrap')
            if chapter_number:
                return chapter_number.text.split(' ')[1]         
            return None
        except NoSuchElementException:
            print("Chapter number element not found.")
            return None
        except Exception as e:
            logger.error(f"Error extracting chapter number: {e}")



    def extract_chapter_info(self, chapter):
            """
            Extracts chapter information from the given chapter element.

            Args:
                chapter: The chapter element to extract information from.

            Returns:
                A dictionary containing the extracted chapter information, including the chapter number,
                chapter name, and chapter link. Returns None if the chapter information could not be extracted.
            """

            chapter_link_elements, link = self.find_chapter_link(chapter)
            chapter_number = self.extract_chapter_number(chapter)
            
            if  chapter_link_elements is None:
                return None
            
            
                
            # split the text into a list of strings and get the first element
            chapter_name = chapter_link_elements.text.split('\n')[0]

            # remove leading and trailing spaces
            chapter_info = {
                'chapter_number': chapter_number if chapter_number else None,
                'chapter_name': chapter_name,
                'chapter_link': link
            }    
            print(chapter_info)
            return chapter_info if chapter_info else None

    

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
            
    def download_images_from_chapter(self, chapter_link, series_name, chapter_number):
        try:
            if os.path.exists(self.prepare_save_path(series_name, "Chapter " + str(chapter_number))):
                logger.warning(
                    f"Folder for {chapter_number} already exists. Exiting.")
                return

            self.navigate_to_chapter(chapter_link)
            self.process_chapter(series_name, chapter_number)

        except NoSuchElementException as e:
            logger.error(f"Element not found: {e}")
        except TimeoutException as e:
            logger.error(f"Loading took too much time: {e}")
        except Exception as e:
            logger.critical(f"Critical error: {e}")
        finally:
            pass

    def prepare_save_path(self, series_name, chapter_number):
        return os.path.join(self.save_path, self.file_operations.sanitize_folder_name(series_name), str(chapter_number))


    def navigate_to_chapter(self, chapter_link):
        """
        Navigates to the given chapter link and waits for the page to load.

        Args:
            chapter_link (str): The URL of the chapter to navigate to.
        """
        self.web_interactions.naviguate(chapter_link, wait_condition=1)
        
        # Inject the network monitoring JavaScript
        self.inject_network_monitoring_js()
        
        # Retry up to 3 times
        for _ in range(3):
            try:
                self.web_interactions.wait_until_element_loaded('class_name', 'overflow-x-auto.flex.items-center.h-full')
                self.wait_for_network_idle()  # Ensure all network requests are completed
                break  # If successful, exit the loop
            except TimeoutException:
                logger.warning("Timeout occurred. Retrying...")
                time.sleep(2)
        else:
            # If all retries failed
            logger.error("Failed to navigate to chapter after multiple attempts.")

    def inject_network_monitoring_js(self):
        script = """
        (function() {
            let open = XMLHttpRequest.prototype.open;
            let send = XMLHttpRequest.prototype.send;
            let fetch = window.fetch;
            let activeRequests = 0;
            let addRequest = () => activeRequests++;
            let removeRequest = () => {
                activeRequests = Math.max(0, activeRequests - 1);
            };
            XMLHttpRequest.prototype.open = function() {
                addRequest();
                this.addEventListener('load', removeRequest);
                this.addEventListener('error', removeRequest);
                this.addEventListener('abort', removeRequest);
                return open.apply(this, arguments);
            };
            XMLHttpRequest.prototype.send = function() {
                return send.apply(this, arguments);
            };
            window.fetch = function() {
                addRequest();
                return fetch.apply(this, arguments)
                    .then(response => {
                        removeRequest();
                        return response;
                    })
                    .catch(error => {
                        removeRequest();
                        throw error;
                    });
            };
            window.getActiveRequests = function() {
                return activeRequests;
            };
        })();
        """
        self.web_interactions.driver.execute_script(script)

    def wait_for_network_idle(self, timeout=30, poll_frequency=0.5):
        WebDriverWait(self.web_interactions.driver, timeout, poll_frequency=poll_frequency).until(
            lambda driver: driver.execute_script('return window.getActiveRequests() === 0')
        )


    def process_chapter(self, series_name, chapter_number):
        """
        Process a chapter of a manga.

        Args:
            series_name (str): The name of the manga series.
            chapter_number (int): The number of the chapter.

        Returns:
            None
        """
        try:
                
            # Initialize the page number and long screenshot taken variables
            page_number = 1
            # Regex pattern to match blob URLs
            blob_pattern = re.compile(r"^blob:.*$")
            # Regex pattern to match PNG URLs and ignore the rest
            png_pattern = re.compile(r"^https://.*mangadex\.network/data/.*\.png$")
            pages = []

            # Retry mechanism to ensure all network logs are captured
            for attempt in range(5):
                print(f"Attempt {attempt + 1} to capture network logs...")
                pages.clear()

                # Fetch network logs and filter them in a single pass
                logs = self.web_interactions.driver.get_log('performance')
                for log in logs:
                    message = json.loads(log['message'])['message']
                    response = message.get('params', {}).get('response', {})
                    url = response.get('url')
                    if url and png_pattern.match(url):
                        page_number = int(url.split('/')[-1].split('-')[0])
                        pages.append((page_number, url))

                # Sort pages by page number
                sorted_pages = sorted(pages, key=lambda x: x[0])

                # Check if we have captured all pages
                if sorted_pages and sorted_pages[0][0] == 1:
                    break
                else:
                    print("Failed to capture all pages, retrying...")
                    time.sleep(2)  # Wait before retrying

            # Check if we captured pages for the current chapter
            if not sorted_pages:
                logger.error(f"Failed to capture any pages for chapter {chapter_number} of {series_name}.")
                return

            # Save the PNG links
            for page_number, page_url in sorted_pages:
                print(f"Saving page {page_number} for chapter {chapter_number}...")
                print(page_url)
                self.file_operations.save_png_links(self.save_path, series_name, chapter_number, page_number, page_url)

        except Exception as e:
            logger.error(f"Error processing chapter: {e}")
            raise


    def handle_error(self):
            """
            Handles errors that occur during manga download.

            If the number of consecutive errors exceeds a certain threshold, the method raises a StopIteration exception.

            Returns:
                True if the error was handled successfully.
            """
            error_count = 0  # Initialize error count
            max_error_count = 3  # Set a maximum number of consecutive errors allowed

            error_count += 1  # Increment error count
            if error_count >= max_error_count:
                print(f"Exceeded maximum consecutive errors ({max_error_count}). Exiting.")
                raise StopIteration
            return True

    def find_mangas_name(self, name):
        try:
            # Navigate to the mangadex website with the search query
           
            # Find all the manga titles corresponding to the input
            # Return the manga titles and their links
            
            # If no manga titles are found, return None
            
            # If an error occurs, raise an exception
            return fetch_and_process_manga_cards(self.web_interactions.driver, name)
        except Exception as e:
            logger.error(f"Error finding mangas: {e}")
            raise
    

    def search_and_select_manga(self):
        try:
            # Ask the user to enter the name of the manga
            name = input("Enter the name of the manga: ")
            mangas = self.find_mangas_name(name)
            
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
                    
                    print(
                        f"You selected: {mangas[int(selected_index) - 1]['title']}")
                    # Fetch all the chapters for the selected manga
                    all_chapters = self.fetch_chapters(mangas[int(selected_index) - 1]['link'])
                    # Return the chapters and the name of the manga
                    return all_chapters, mangas[int(selected_index) - 1]['title']
                else:
                    # make the user re-enter the number
                    print("Invalid number. Please enter a valid number.")
                    return self.search_and_select_manga()
            else:
                print("No manga found. Please try again\n")

                # make the user re-enter the name of the manga
                return self.search_and_select_manga()
        except Exception as e:
            logger.error(f"Error searching and selecting manga: {e}")
            raise
        except KeyboardInterrupt as e:
            # Clean up the resources used by the program
            self.web_interactions.cleanup()            
            raise