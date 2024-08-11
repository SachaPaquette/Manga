import json,time, os, re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import  NoSuchElementException, TimeoutException
from Config.config import Config
from MangaDownload.FileOperations import FileOperations
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.WebInteractions import logger
from MangaFetch.FetchOperations import fetch_and_process_manga_cards

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
            self.web_interactions.wait_until((By.CLASS_NAME, Config.CHAPTER_CARDS), multiple=True)
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
            chapters_array += self.process_chapter_cards(self.web_interactions.driver.find_elements(By.CLASS_NAME, Config.CHAPTER_CARDS))

            if not self.web_interactions.click_next_page():
                break

            self.web_interactions.wait_until_page_loaded(1)

        return chapters_array
  
    def fill_missing_chapter_numbers(self, chapters_array):
        """
        Fills missing chapter numbers in the chapters array in descending order.

        :param chapters_array: List of chapter objects.
        :type chapters_array: list
        """
        last_chapter_number = None

        for i in range(len(chapters_array) - 1, -1, -1):
            chapter = chapters_array[i]
            if 'chapter_number' in chapter and chapter['chapter_number'] is not None:
                last_chapter_number = chapter['chapter_number']
            else:
                if last_chapter_number is not None:
                    chapter['chapter_number'] = last_chapter_number + 1
                else:
                    chapter['chapter_number'] = len(chapters_array) - i
                last_chapter_number = chapter['chapter_number']


    def process_chapter_cards(self, chapter_cards):
        """
        Extracts chapter information from the given chapter cards and returns an array of chapter info objects
        along with the number of the first chapter.

        Args:
            chapter_cards (list): A list of chapter cards to extract information from.

        Returns:
            list: A list of chapter info objects.
        """
        chapters_array = []

        for chapter in chapter_cards:
            try:
                # Extract the chapter info from the chapter card
                chapter_info = self.extract_chapter_info(chapter)
                if chapter_info is None:
                    logger.warning(f"Chapter info extraction returned None for chapter: {chapter}")
                    continue

                # Check if the chapter number has already been added
                if chapter_info["chapter_name"] != self.previous_chapter_name:
                    chapters_array.append(chapter_info)
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
            bool: True if the link is unsupported (from mangaplus), False otherwise.
        """
        return "mangaplus" in link


    def find_chapter_link(self, chapter):
        """
        Finds the chapter link elements and flag image elements for a given chapter.

        Args:
            chapter: The chapter element to search for links and flag images.

        Returns:
            tuple: A tuple (link element, link URL) corresponding to the English title, or None if not found.
        """
        try:
            # Find all chapter link elements within the chapter
            chapter_link_elements = chapter.find_elements(by=By.CLASS_NAME, value=Config.CHAPTER_LINK)
            
            for link in chapter_link_elements:
                try:
                    # Check if the link has an image element with title attribute 'English'
                    img_element = link.find_element(by=By.TAG_NAME, value=Config.IMG)
                    if img_element.get_attribute('title') == 'English':
                        link_url = link.find_element(by=By.TAG_NAME, value=Config.HYPERLINK).get_attribute(Config.HREF)
                        if link_url and not self.unsupported_website(link_url):
                            return link, link_url
                except NoSuchElementException:
                    continue

        except NoSuchElementException as e:
            logger.error(f"No such element found: {e}")
        except Exception as e:
            logger.error(f"Error finding chapter link: {e}")

        return None




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
            if  chapter_link_elements is None or link is None:
                return None
            # split the text into a list of strings and get the first element
            chapter_name = chapter_link_elements.text.split('\n')[0]

            # remove leading and trailing spaces
            chapter_info = {
                'chapter_name': chapter_name,
                'chapter_link': link
            }    
            
            return chapter_info if chapter_info else None


    def download_images_from_chapter(self, chapter_link, series_name, chapter_number):
        try:
            if self.file_operations.check_chapter_folder_exist(series_name, chapter_number):
                logger.info(f"Chapter {chapter_number} already downloaded. Skipping...")
                return
            # Navigate to the chapter link and process the chapter
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



    def navigate_to_chapter(self, chapter_link):
        """
        Navigates to the given chapter link and waits for the page to load.

        Args:
            chapter_link (str): The URL of the chapter to navigate to.
        """
        # Navigate to the chapter link
        self.web_interactions.naviguate(chapter_link)
        # Inject the network monitoring JavaScript to wait until all network requests are completed
        self.inject_network_monitoring_js()
    
        # Retry up to 3 times if the page does not load
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
        """
        Wait until the network is idle, i.e., no active network requests.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            bool: True if the network became idle, False if timed out.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            active_requests = self.web_interactions.driver.execute_script("return window.getActiveRequests();")
            if active_requests == 0:
                return True
            time.sleep(poll_frequency)
        return False


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
            pages = self.retry_capture_network_logs()
            if not pages:
                logger.error(f"Failed to capture any pages for chapter {chapter_number} of {series_name}.")
                return
            self.file_operations.save_chapter_pages(series_name, chapter_number, pages)
            
            #self.save_chapter_pages(series_name, chapter_number, pages)
        except Exception as e:
            logger.error(f"Error processing chapter: {e}")
            raise

    def retry_capture_network_logs(self, max_attempts=5):
        """
        Retry capturing network logs to ensure all pages are captured.

        Args:
            max_attempts (int): Maximum number of attempts to capture network logs.

        Returns:
            list: A list of tuples containing page numbers and URLs.
        """
        pages = []
        for attempt in range(max_attempts):
            if attempt + 1 > 1:
                print(f"Attempt {attempt + 1} to capture network logs...")
            try:     
                pages = self.capture_network_logs(re.compile(r"^https://.*mangadex\.network/data/.*\.(png|jpg)$"))
                if pages and pages[0][0] == 1:
                    break
                else:
                    print("Failed to capture all pages, retrying...")
                    time.sleep(1)
                return pages
            except Exception as e:
                logger.error(f"Error retrying to capture network logs: {e}")       
        return pages
    def capture_network_logs(self, png_pattern):
        """
        Capture network logs and filter PNG URLs.

        Args:
            png_pattern (re.Pattern): Compiled regex pattern to match PNG URLs.

        Returns:
            list: A list of tuples containing page numbers and URLs.
        """
        try:
            
            
            return sorted(self.extract_png_urls(self.web_interactions.driver.get_log('performance'), png_pattern), key=lambda x: x[0])
        except Exception as e:
            logger.error(f"Error capturing network logs: {e}")
            return []
        
        
    def extract_png_urls(self, logs, png_pattern):
        """
        Extract PNG URLs and their corresponding page numbers from network logs.

        Args:
            logs (list): List of log entries from the browser.
            png_pattern (re.Pattern): Compiled regex pattern to match PNG URLs.

        Returns:
            list: A list of tuples containing page numbers and URLs.
        """
        pages = []
        for log in logs:
            url = self.extract_url_from_log(log)
            if url and png_pattern.match(url):
                page_number = self.extract_page_number(url)
                if page_number is not None:
                    pages.append((page_number, url))
                else:
                    logger.warning(f"Invalid page number in URL: {url}")
        return pages

    def extract_url_from_log(self, log):
        """
        Extract the URL from a log entry.

        Args:
            log (dict): A single log entry.

        Returns:
            str or None: The extracted URL or None if extraction fails.
        """
        try:
            return json.loads(log['message']).get('message', {}).get('params', {}).get('response', {}).get('url')
        except Exception as e:
            logger.error(f"Error extracting URL from log: {e}")
            return None

    def extract_page_number(self, url):
        """
        Extracts the page number from the given URL.

        Args:
            url (str): The URL to extract the page number from.

        Returns:
            int or None: The page number if found, otherwise None.
        """
        try:
            # Extract the page number from the URL
            match = re.search(r'\d+', url.split('/')[-1].split('-')[0])
            if match:
                return int(match.group())
        except Exception as e:
            logger.error(f"Error extracting page number from URL {url}: {e}")
        return None
        
    def save_chapter_pages(self, series_name, chapter_number, pages):
        """
        Save the captured PNG links for the chapter.

        Args:
            series_name (str): The name of the manga series.
            chapter_number (int): The number of the chapter.
            pages (list): A list of tuples containing page numbers and URLs.

        Returns:
            None
        """
        for page_number, page_url in pages:
            print(f"Saving page {page_number} for chapter {chapter_number}...")
            self.file_operations.save_png_links(self.save_path, series_name, chapter_number, page_number, page_url)
        
    def search_and_select_manga(self):
        try:
            # Ask the user to enter the name of the manga and fetch the manga cards
            mangas = self.fetch_and_process_manga_cards(self.prompt_manga_name())
            
            if not mangas:
                print("No manga found. Please try again.\n")
                return self.search_and_select_manga()

            self.display_search_results(mangas)

            selected_index = self.prompt_manga_selection(len(mangas))
            if selected_index == 0:
                print("Exiting.")
                return [], ""

            selected_manga = mangas[selected_index - 1]
            print(f"You selected: {selected_manga['title']}")

            all_chapters = self.fetch_chapters(selected_manga['link'])
            return all_chapters, selected_manga['title']
        
        except KeyboardInterrupt:
            print("\nExiting.")
            self.cleanup_resources()
            raise
        except Exception as e:
            logger.error(f"Error searching and selecting manga: {e}")
            raise

    def prompt_manga_name(self):
        """
        Prompts the user to enter the name of the manga.

        Returns:
            str: The name of the manga entered by the user.
        """
        return input("Enter the name of the manga: ")

    def fetch_and_process_manga_cards(self, manga_name):
        """
        Fetches and processes manga cards based on the provided manga name.

        Args:
            manga_name (str): The name of the manga to search for.

        Returns:
            list: A list of manga objects.
        """
        return fetch_and_process_manga_cards(self.web_interactions.driver, manga_name)

    def display_search_results(self, mangas):
        """
        Displays the search results.

        Args:
            mangas (list): A list of manga objects.
        """
        print("Search results:")
        for i, manga in enumerate(mangas):
            print(f"{i + 1}. {manga['title']}")

    def prompt_manga_selection(self, num_mangas):
        """
        Prompts the user to select a manga from the search results.

        Args:
            num_mangas (int): The number of manga options available.

        Returns:
            int: The index of the selected manga.
        """
        while True:
            try:
                selected_index = input("Enter the number of the manga you want to download (or '0' to exit): ")
                if selected_index.isdigit():
                    selected_index = int(selected_index)
                    if 0 <= selected_index <= num_mangas:
                        return selected_index
                print(f"Invalid number. Please enter a number between 0 and {num_mangas}.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")


    def cleanup_resources(self):
        """
        Cleans up resources used by the program.
        """
        #self.web_interactions.cleanup()
        pass