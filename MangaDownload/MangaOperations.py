import json, time, os, re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from concurrent.futures import ThreadPoolExecutor
from Config.config import Config, ScriptConfig
from MangaDownload.FileOperations import FileOperations
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.WebInteractions import logger
from MangaFetch.FetchOperations import fetch_and_process_manga_cards

class MangaDownloader:

    def __init__(self, web_interactions=None, file_operations=None):
        self._web_interactions = web_interactions
        self._file_operations = file_operations
        self.save_path = os.getenv("SAVE_PATH", Config.DEFAULT_SAVE_PATH)
        if not os.path.isdir(self.save_path):
            raise ValueError(f"Invalid save path: {self.save_path}")

    @property
    def web_interactions(self):
        if not self._web_interactions:
            self._web_interactions = WebInteractions()
        return self._web_interactions

    @property
    def file_operations(self):
        if not self._file_operations:
            self._file_operations = FileOperations(self.web_interactions)
        return self._file_operations

    def print_chapter_info(self, chapter):
        print(f"{chapter['chapter_number']}, {chapter['chapter_name']}, {chapter['chapter_link']}")

    def fetch_chapters(self, link):
        if not link or not isinstance(link, str):
            logger.error(f"Invalid URL provided: {link}")
            return []

        self.web_interactions.navigate(link, wait_condition=1)
        try:
            self.web_interactions.wait_until((By.CLASS_NAME, Config.CHAPTER_CARDS), multiple=True)
            chapters = self.collect_chapters()
            self.fill_missing_chapter_numbers(chapters)
            return chapters
        except Exception as e:
            logger.error(f"Error fetching chapters: {e}")
            return []

    def collect_chapter_cards(self, url):
        """
        Collect chapter cards from a specific page URL.
        """
        try:
            self.web_interactions.navigate(url)
            # Wait until chapter cards are available
            self.web_interactions.wait_until((By.CLASS_NAME, Config.CHAPTER_CARDS), multiple=True)
            # Re-fetch chapter cards after ensuring the page is loaded
            chapter_cards = self.web_interactions.driver.find_elements(By.CLASS_NAME, Config.CHAPTER_CARDS)
            return self.process_chapter_cards(chapter_cards)
        except Exception as e:
            logger.error(f"Error collecting chapter cards from {url}: {e}")
            return []

    def collect_chapters(self):
        chapters = []
        while True:
            chapter_cards = self.web_interactions.driver.find_elements(By.CLASS_NAME, Config.CHAPTER_CARDS)
            chapters.extend(self.process_chapter_cards(chapter_cards))
            if not self.web_interactions.click_next_page():
                break
            self.web_interactions.wait_until_page_loaded(1)
        return chapters


    def fill_missing_chapter_numbers(self, chapters):
        next_number = len(chapters)
        for chapter in chapters:
            if 'chapter_number' not in chapter or chapter['chapter_number'] is None:
                chapter['chapter_number'] = next_number
                next_number -= 1

    def process_chapter_cards(self, chapter_cards):
        with ThreadPoolExecutor() as executor:
            results = list(filter(None, executor.map(self.extract_chapter_info, chapter_cards)))

        seen = set()
        return [chapter for chapter in results if chapter['chapter_name'] not in seen and not seen.add(chapter['chapter_name'])]

    def extract_chapter_info(self, chapter):
        link_element, link_url = self.find_chapter_link(chapter)
        if not link_element or not link_url:
            return None

        return {
            'chapter_name': link_element.text.strip().split('\n')[0],
            'chapter_link': link_url
        }

    def find_chapter_link(self, chapter):
        try:
            for link in chapter.find_elements(By.CLASS_NAME, Config.CHAPTER_LINK):
                img_element = link.find_element(By.TAG_NAME, Config.IMG)
                if img_element.get_attribute('title') == 'English':
                    link_url = link.find_element(By.TAG_NAME, Config.HYPERLINK).get_attribute(Config.HREF)
                    if link_url and not 'mangaplus' in link_url:
                        return link, link_url
        except NoSuchElementException as e:
            logger.error(f"No such element found: {e}")
        except Exception as e:
            logger.error(f"Error finding chapter link: {e}")
        return None, None

    def download_images_from_chapter(self, manga_chapter):
        try:
            chapter_link, series_name, chapter_number = manga_chapter
            if self.file_operations.check_cbz_file_exist(series_name, chapter_number):
                logger.info(f"Chapter {chapter_number} already exists for {series_name}. Skipping download.")
                return

            self.navigate_to_chapter(chapter_link)
            self.process_chapter(series_name, chapter_number)
        except Exception as e:
            logger.critical(f"Critical error during download: {e}")

    def navigate_to_chapter(self, chapter_link):
        self.web_interactions.navigate(chapter_link)
        self.inject_network_monitoring_js()
        for _ in range(3):
            try:
                self.web_interactions.wait_until_element_loaded('class_name', 'overflow-x-auto.flex.items-center.h-full')
                self.wait_for_network_idle()
                break
            except TimeoutException:
                logger.warning("Timeout occurred. Retrying...")
                time.sleep(2)
        else:
            logger.error("Failed to navigate to chapter after multiple attempts.")

    def inject_network_monitoring_js(self):
        self.web_interactions.driver.execute_script(ScriptConfig.javascript_network_script)

    def wait_for_network_idle(self, timeout=30, poll_frequency=0.5):
        end_time = time.time() + timeout
        while time.time() < end_time:
            active_requests = self.web_interactions.driver.execute_script("return window.getActiveRequests();")
            if active_requests == 0:
                return True
            time.sleep(poll_frequency)
        return False

    def process_chapter(self, series_name, chapter_number):
        try:
            pages = self.retry_capture_network_logs()
            if not pages:
                logger.error(f"Failed to capture any pages for chapter {chapter_number} of {series_name}.")
                return
            self.file_operations.save_chapter_pages(series_name, chapter_number, pages)
        except Exception as e:
            logger.error(f"Error processing chapter: {e}")

    def retry_capture_network_logs(self, max_attempts=5):
        pages = []
        for attempt in range(max_attempts):
            try:
                pages = self.capture_network_logs(re.compile(r"^https://.*mangadex\.network/data/.*\.(png|jpg)$"))
                if pages and pages[0][0] == 1:
                    break
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error retrying network logs capture: {e}")
        return pages

    def capture_network_logs(self, png_pattern):
        try:
            logs = self.web_interactions.driver.get_log('performance')
            return sorted(self.extract_png_urls(logs, png_pattern), key=lambda x: x[0])
        except Exception as e:
            logger.error(f"Error capturing network logs: {e}")
            return []

    def extract_png_urls(self, logs, png_pattern):
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
        try:
            return json.loads(log['message']).get('message', {}).get('params', {}).get('response', {}).get('url')
        except Exception as e:
            logger.error(f"Error extracting URL from log: {e}")
            return None

    def extract_page_number(self, url):
        try:
            match = re.search(r'/(\d+)-', url)
            if match:
                return int(match.group(1))
            else:
                logger.warning(f"No valid page number found in URL: {url}")
        except Exception as e:
            logger.error(f"Error extracting page number from URL {url}: {e}")
        return None


    def search_and_select_manga(self):
        try:
            mangas = self.fetch_and_process_manga_cards(self.prompt_manga_name())
            if not mangas:
                print("No manga found. Please try again.")
                return self.search_and_select_manga()

            self.display_search_results(mangas)
            selected_index = self.prompt_manga_selection(len(mangas))

            if selected_index == 0:
                print("Exiting.")
                return [], ""

            selected_manga = mangas[selected_index - 1]
            print(f"You selected: {selected_manga['title']}")
            return self.fetch_chapters(selected_manga['link']), selected_manga['title']

        except Exception as e:
            logger.error(f"Error searching and selecting manga: {e}")

    def prompt_manga_name(self):
        return input("Enter the name of the manga: ")

    def fetch_and_process_manga_cards(self, manga_name):
        return fetch_and_process_manga_cards(self.web_interactions.driver, manga_name)

    def display_search_results(self, mangas):
        print("\nSearch Results:\n" + "="*30)
        for i, manga in enumerate(mangas):
            print(f"{i + 1}. {manga['title']}")
        print("="*30 + "\n")

    def prompt_manga_selection(self, num_mangas):
        """
        Prompt the user to select a manga from the search results.

        Args:
            num_mangas (int): The total number of manga options available.

        Returns:
            int: The index of the selected manga.
        """
        prompt_message = f"Select manga (1-{num_mangas}, or 0 to exit): "

        while True:
            try:
                selection = int(input(prompt_message).strip())
                if 0 <= selection <= num_mangas:
                    return selection
                print(f"⚠️ Invalid input. Please enter a number between 0 and {num_mangas}.")
            except ValueError:
                print("❌ Invalid input. Please enter a valid number.")
