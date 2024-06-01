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
        :return type: list
        """
        logger.info(f"Fetching chapters for link: {link}")
        self.web_interactions.naviguate(link)  # Navigate to the link
        try:
            self.web_interactions.wait_for_chapter_cards()
            # Check if there are chapters on the page
            chapter_cards = self.web_interactions.driver.find_elements(
                by=By.CLASS_NAME, value=Config.CHAPTER_CARDS)
            
            # Loop while there are still chapters to fetch
            
            chapters_array = self.process_chapter_cards(chapter_cards)
          
            while True:  
                
                if not self.web_interactions.click_next_page():  # Check the return value
                    break

                self.web_interactions.wait_for_next_page()  # Wait for the next page to load
                chapter_cards = self.web_interactions.driver.find_elements(
                    by=By.CLASS_NAME, value=Config.CHAPTER_CARDS)  # Find all the chapter cards on the page
                # Process the chapter cards and append the results to the array
                chapters_array += self.process_chapter_cards(
                    chapter_cards)

            print(f"Found {len(chapters_array)} chapters.")
            print(chapters_array)        
        
            # Add the chapter numbers when the chapter_number is none
            for i, chapter in enumerate(chapters_array):
                if chapter['chapter_number'] is None:
                    if i > 0 and chapters_array[i - 1]['chapter_number'] is not None:
                        chapter['chapter_number'] = chapters_array[i - 1]['chapter_number'] - 1
                    elif i < len(chapters_array) - 1 and chapters_array[i + 1]['chapter_number'] is not None:
                        chapter['chapter_number'] = chapters_array[i + 1]['chapter_number'] + 1
                    else:
                        chapter['chapter_number'] = len(chapters_array) - i
            
                    
                        
                
            
        except Exception as e:
            logger.error(f"Error fetching chapters: {e}")
            raise
        finally:
            # Check if there are chapters to return
            if chapters_array:
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
            The chapter link element corresponding to the English title, or None if not found.
        """
        try:
            # Find all chapter link elements within the chapter
            chapter_link_elements = chapter.find_elements(by=By.CLASS_NAME, value=Config.CHAPTER_LINK)
            
            for link in chapter_link_elements:
                try:
                    # Check if the link has an image element with title attribute 'English'
                    img_element = link.find_element(by=By.TAG_NAME, value=Config.IMG)
                    if img_element.get_attribute('title') == 'English':
                        return link
                except NoSuchElementException:
                    continue
            
            return None

        except NoSuchElementException as e:
            print(f"NoSuchElementException encountered: {e}")
            return None
        except Exception as e:
            print(f"Error finding chapter link: {e}")
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

            chapter_link_elements = self.find_chapter_link(chapter)
            chapter_number = self.extract_chapter_number(chapter)
            
            if  chapter_link_elements is None:
                return None
            
            
                
            # split the text into a list of strings and get the first element
            chapter_name = chapter_link_elements.text.split('\n')[0]
            
            
                
            link = chapter_link_elements.find_element(
                by=By.TAG_NAME, value=Config.HYPERLINK).get_attribute(Config.HREF)

            # check if the website is supported
            link = self.unsupported_website(link)

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
            
    def long_manga(self, long_screenshot_taken, series_name, chapter_number):
        long_screenshot_taken = True # Set the long screenshot boolean variable to True to prevent taking another long screenshot

        # Process long manga differently
        self.file_operations.save_long_screenshot(
        self.web_interactions.driver, self.save_path, series_name, chapter_number, None)
        return long_screenshot_taken
    
    def download_images_from_chapter(self, chapter_link, series_name, chapter_number):
        try:
            if os.path.exists(self.prepare_save_path(series_name, "Chapter " + str(chapter_number))):
                logger.warning(
                    f"Folder for {chapter_number} already exists. Exiting.")
                return

            self.navigate_to_chapter(chapter_link)
            #previous_chapter_id = self.extract_chapter_id(chapter_link)
            #is_long_manga = Config.LONG_MANGA_IMAGE in self.web_interactions.check_element_exists()
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


    def process_chapter(self, series_name, chapter_number):
        """
        Process a chapter of a manga.

        Args:
            series_name (str): The name of the manga series.
            chapter_number (int): The number of the chapter.

        Returns:
            None
        """
        # Initialize the page number and long screenshot taken variables
        page_number = 1
        # Regex pattern to match blob URLs
        blob_pattern = re.compile(r"^blob:.*$")
        # Regex pattern to match PNG URLs and ignore the rest
        png_pattern = re.compile(r"^https://.*mangadex\.network/data/.*\.png$")
        pages = []

            # Get the network logs
        for log in self.web_interactions.driver.get_log('performance'):
            if 'response' in json.loads(log['message'])['message']['params']:
                response = json.loads(log['message'])['message']['params']['response']
                
                if response.get('url'):
                    blob_match = blob_pattern.match(response['url'])
                    png_match = png_pattern.match(response['url'])
                    if png_match:
                        
                        page_number = int(response['url'].split('/')[-1].split('-')[0])
                        pages.append((page_number, response['url']))

        
        sorted_pages = sorted(pages, key=lambda x: x[0])
        for page_number, page_url in sorted_pages:
            self.file_operations.save_png_links(self.save_path, series_name, chapter_number, page_number, page_url)



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