import os, requests, re, io, concurrent.futures
import time
# import threadpoolExecutor
from concurrent.futures import ThreadPoolExecutor
import zipfile
from Config.config import Config
# Configure logging
from MangaDownload.WebInteractions import logger
from MangaDownload.WebInteractions import WebInteractions

from PIL import Image
import pyzipper
class FileOperations:
    def __init__(self, web_interactions=None):
        """Initialize the FileOperations instance. 

        Args:
            web_interactions (WebInteractions): The WebInteractions instance.
            driver (WebDriver): The Selenium WebDriver instance.
        """
        if not web_interactions:
            from MangaDownload.WebInteractions import WebInteractions
            web_interactions = WebInteractions()
        self.web_interactions = web_interactions
        # Initialize the WebDriver instance
        self.driver = web_interactions.driver
        # Store the original tab handle
        self.original_tab_handles = None
        # Store the last processed URL
        self.last_processed_url = None
        # Store the unique base64 data (to avoid duplicates)
        self.unique_base64_data = set()
        # Store the last loaded image source (to check if the image is loaded)
        self.last_loaded_img_src = None
        self.max_workers_number = 30
        
        self.save_path = os.getenv("SAVE_PATH", Config.DEFAULT_SAVE_PATH)
        if not os.path.isdir(self.save_path):
            raise ValueError(f"Save path '{self.save_path}' is not a valid directory.")


    def sanitize_folder_name(self, folder_name):
        """
        Sanitize the folder name by removing or replacing any characters that are not allowed in a folder name.

        Args:
            folder_name (str): The folder name to sanitize.

        Returns:
            str: The sanitized folder name.
        """
        # Replace invalid characters with a space and strip leading/trailing spaces
        sanitized_name = re.sub(r'[<>:"/\\|?*]', ' ', folder_name).strip()

        # Set the folder name to "UnknownManga" if it is empty after sanitization
        return sanitized_name if sanitized_name else "UnknownManga"



    def create_screenshot_filename(self, page_number, part_number=0):
        return f"page_{page_number}_{part_number}.png"






    def bulk_save_png_links(self, page_data):
        """
        Save multiple PNG images from URLs to a single .cbz file.

        Args:
            page_data (list): A list of tuples containing series name, chapter number, page number, and image URL.

        Returns:
            None
        """
        def process_image(data):
            series_name, chapter_number, page_number, img_src = data
            try:
                img_data = self.download_image(img_src)
                if not img_data:
                    logger.error(f"Failed to download image from {img_src}")
                    return None
                return (series_name, chapter_number, page_number, img_data)
            except Exception as e:
                logger.error(f"Error saving PNG link {img_src} for chapter {chapter_number}, page {page_number}: {e}")
            return None

        try:
            # Ensure all images are loaded
            #if not self.web_interactions.wait_for_images_to_load():
             #   logger.warning("Not all images were fully loaded. Proceeding with available images.")
            # Process images concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers_number) as executor:
                image_data_list = list(executor.map(process_image, page_data))

            if image_data_list:
                valid_image_data_list = [item for item in image_data_list if item]
                valid_image_data_list.sort(key=lambda x: x[2])  # Sort by page number
                print(f"Saving {len(valid_image_data_list)} images for chapter ...")
            else:
                logger.error("No valid image data to save.")
                return

            # Create a .cbz file for the chapter
            self.create_cbz_file(valid_image_data_list)
        except Exception as e:
            logger.error(f"Error saving PNG links for chapter: {e}")





    def create_cbz_filename(self, series_name, chapter_number):
        # Create the .cbz filename for the chapter
        return f"{series_name} Chapter {chapter_number}.cbz"

    def create_cbz_folder_path(self, folder_path, cbz_filename):
        # Use the existing folder_path directly for the .cbz file
        return os.path.join(folder_path, cbz_filename)


    def create_folder_path(self, series_name):
        # Get the first letter of the series name
        sanitized_series_name = self.sanitize_folder_name(series_name)
        
        # Create the folder path for the series ex: ./Mangas/A/Attack on Titan
        return os.path.join(self.save_path, sanitized_series_name[0].upper(), sanitized_series_name)
    
    def create_cbz_file(self, image_data_list):
        try:
            series_name, chapter_number = self.get_series_and_chapter_info(image_data_list)
            folder_path = self.create_folder_path(series_name)
            os.makedirs(folder_path, exist_ok=True)
            cbz_file_path = self.create_cbz_folder_path(folder_path, self.create_cbz_filename(series_name, chapter_number))
            print(f"Creating .cbz file for chapter {chapter_number}...")

            with zipfile.ZipFile(cbz_file_path, "w") as cbz_file:
                for series_name, chapter_number, page_number, img_data in image_data_list:
                    # Validate img_data
                    if not isinstance(img_data, bytes) or not img_data:
                        logger.error(f"Invalid image data for page {page_number}. Skipping...")
                        continue

                    # Pass cbz_file.namelist() instead of cbz_file
                    screenshot_filename = self.get_screenshot_filename(page_number, cbz_file.namelist())
                    cbz_file.writestr(screenshot_filename, img_data)

            logger.info(f"Saved chapter {chapter_number} as {cbz_file_path}")
        except Exception as e:
            logger.error(f"Error creating .cbz file for chapter {chapter_number}: {e}")



    def get_series_and_chapter_info(self, image_data_list):
        return image_data_list[0][:2]

    def get_screenshot_filename(self, page_number, existing_files):
        # Generate base filename
        base_filename = self.create_screenshot_filename(page_number, page_number)
        extension = base_filename.split('.')[-1]
        name = '.'.join(base_filename.split('.')[:-1])

        # Ensure uniqueness using a set for efficiency
        filename = base_filename
        if filename not in existing_files:
            return filename

        # Find the next available unique filename
        for counter in range(1, len(existing_files) + 2):
            filename = f"{name}_{counter}.{extension}"
            if filename not in existing_files:
                return filename



    def download_image(self, img_src):
        """
        Download an image from the given URL.

        Args:
            img_src (str): The URL of the image to download.

        Returns:
            bytes or None: The binary content of the image if successful, None otherwise.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'} 
            with requests.get(img_src, headers=headers, timeout=10, stream=True) as response:
                response.raise_for_status()

                # Validate the content type
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.error(f"URL {img_src} did not return an image. Content-Type: {content_type}")
                    return None

                # Read the image in chunks
                return b"".join(chunk for chunk in response.iter_content(chunk_size=8192) if chunk)
        except requests.Timeout:
            logger.error(f"Timeout while downloading image from {img_src}")
        except requests.RequestException as e:
            logger.error(f"Error downloading image from {img_src}: {e}")
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
        try:
            
            page_data = []

            for page_number, page_url in pages:
                page_data.append((series_name, chapter_number, page_number, page_url ))
            print(f"Saving {len(page_data)} pages for chapter {chapter_number}...")
            self.bulk_save_png_links(page_data)
        except Exception as e:
            logger.error(f"Error saving chapter pages for chapter {chapter_number}: {e}")
        
    def save_image_from_url(self, img_src, folder_path, file_name):
        """
        Downloads an image from the given URL and saves it to the specified folder with the given file name.

        Args:
            img_src (str): The URL of the image to download.
            folder_path (str): The path to the folder where the image will be saved.
            file_name (str): The name to save the image file as.

        Returns:
            bool: True if the image was successfully saved, False otherwise.
        """
        try:
            response = requests.get(img_src)
            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
            # Save the image to the specified folder
            Image.open(io.BytesIO(response.content)).save(os.path.join(folder_path, file_name))
            return True
        except requests.RequestException as e:
            logger.error(f"Error downloading image from {img_src}: {e}")
            return False
        except IOError as e:
            logger.error(f"Error saving image to {os.path.join(folder_path, file_name)}: {e}")
            return False


    def prepare_save_path(self, series_name, chapter_number):
        # Prepare the save path for the current chapter
        return os.path.join(self.save_path, self.sanitize_folder_name(series_name), chapter_number)
    
    def check_cbz_file_exist(self, series_name, chapter_number):
        # Generate the sanitized series folder path
        folder_path = self.create_folder_path(series_name)
        # Generate the .cbz file path for the chapter
        cbz_file_path = self.create_cbz_folder_path(folder_path, self.create_cbz_filename(series_name, chapter_number))
        # Check if the .cbz file already exists
        return os.path.exists(cbz_file_path)
