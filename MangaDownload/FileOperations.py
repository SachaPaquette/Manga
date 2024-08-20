import os, requests, re, io, concurrent.futures
# import threadpoolExecutor
from concurrent.futures import ThreadPoolExecutor
import zipfile
from Config.config import Config
# Configure logging
from MangaDownload.WebInteractions import logger
from PIL import Image
import pyzipper
class FileOperations:
    failed_images = []  # Array to store the images that failed to save

    def __init__(self, web_interactions):
        """Initialize the FileOperations instance. 

        Args:
            web_interactions (WebInteractions): The WebInteractions instance.
            driver (WebDriver): The Selenium WebDriver instance.
        """
        # Initialize the WebInteractions instance
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
        
        if os.getenv("SAVE_PATH") is not None:
            self.save_path = os.getenv("SAVE_PATH")
        else:
            print("SAVE_PATH environment variable not found.")
            self.save_path = Config.DEFAULT_SAVE_PATH
            print(f"Using default save path to save mangas: {self.save_path}")

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


    def create_folder_path(self, save_path, sanitized_folder_name, chapter_number):
        """Function to generate the folder path. This will be used to save the manga chapters.

        Args:
            save_path (string): The path to save the manga.
            sanitized_folder_name (string): The sanitized folder name.
            chapter_number (int): The chapter number.

        Returns:
            string: The folder path.
        """
        return os.path.join(save_path, sanitized_folder_name, chapter_number)

    def create_screenshot_filename(self, page_number, part_number=0):
        return f"page_{page_number}_{part_number}.png"

    def create_screenshot_filepath(self, folder_path, screenshot_filename):
        """Function to generate the screenshot filepath. This will be used to save the screenshot.

        Args:
            folder_path (string): The folder path to save the screenshot.
            screenshot_filename (string): The screenshot filename.

        Returns:
            string: The screenshot filepath.
        """
        return os.path.join(folder_path, screenshot_filename)

    def create_chapter_folder(self, save_path, series_name, chapter_number, page_number=None):
        """
        Creates the folder path for a chapter and optionally the screenshot filepath for a page.
        This function also creates the folder if it doesn't exist.

        Args:
            save_path (str): The path to save the manga.
            series_name (str): The name of the manga series.
            chapter_number (str): The chapter number. (e.g., Chapter 1)
            page_number (int, optional): The page number. Defaults to None.

        Returns:
            tuple: A tuple containing the folder path and optionally the screenshot filepath.
        """
        # Sanitize the series name and create the folder path
        folder_path = self.create_folder_path(save_path, self.sanitize_folder_name(series_name), f"Chapter {chapter_number}")
        # Create the folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        # If page number is provided, create the screenshot filepath
        if page_number:
            return folder_path, self.create_screenshot_filepath(folder_path, self.create_screenshot_filename(page_number))
        return folder_path

    def save_png_links(self, save_path, series_name, chapter_number, page_number, img_src):
        """
        Save a PNG image from a URL to the specified folder path, using the chapter and page numbers.

        Args:
            save_path (str): The path to save the manga.
            series_name (str): The name of the manga series.
            chapter_number (int or str): The chapter number.
            page_number (int): The page number.
            img_src (str): The URL of the PNG image to save.

        Returns:
            int: The next page number.
        """
        try:
            folder_path, _ = self.create_chapter_folder(save_path, series_name, chapter_number, page_number)
            self.save_image_from_url(img_src, folder_path, self.create_screenshot_filename(page_number))
            return page_number + 1
        except Exception as e:
            logger.error(f"Error saving PNG link {img_src} for chapter {chapter_number}, page {page_number}: {e}")
            return page_number  # Return the current page number if there's an error

    def bulk_save_png_links(self, save_path, page_data):
        """
        Save multiple PNG images from URLs to a single .cbz file.

        Args:
            save_path (str): The path to save the manga.
            page_data (list): A list of tuples containing series name, chapter number, page number, and image URL.

        Returns:
            None
        """
        def process_image(data):
            series_name, chapter_number, page_number, img_src = data
            try:
                img_data = self.download_image(img_src)
                if img_data:
                    processed_img_data = self.processing_image(img_data)
                    # Return a tuple for each image part
                    return [(series_name, chapter_number, page_number + i, part) 
                            for i, part in enumerate(processed_img_data)]
            except Exception as e:
                logger.error(f"Error saving PNG link {img_src} for chapter {chapter_number}, page {page_number}: {e}")
            return None
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
                image_data_list = list(executor.map(process_image, page_data))
            
            if image_data_list:
                flattened_image_data_list = [item for sublist in image_data_list if sublist for item in sublist]
                flattened_image_data_list.sort(key=lambda x: x[2])  # Sort by page number
                print(f"Saving {len(flattened_image_data_list)} images for chapter ...")
            else:
                logger.error("image_data_list is None")
                return
            
            
            # Create a .cbz file for the chapter
            self.create_cbz_file(flattened_image_data_list)
        except Exception as e:
            logger.error(f"Error saving PNG links for chapter: {e}")


    def create_cbz_filename(self, series_name, chapter_number):
        # Create the .cbz filename for the chapter
        return f"{series_name} Chapter {chapter_number}.cbz"

    def join_cbz_filename(self, folder_path, cbz_filename):
        return os.path.join(folder_path, cbz_filename)

    def create_folder_path(self, series_name):
        # Create the folder path for the series
        return os.path.join(self.save_path, self.sanitize_folder_name(series_name))
    
    def create_cbz_file(self, image_data_list):
        try:
            series_name, chapter_number = self.get_series_and_chapter_info(image_data_list)
            folder_path = self.create_folder_path(series_name)
            os.makedirs(folder_path, exist_ok=True)
            
            cbz_file_path = self.join_cbz_filename(folder_path, self.create_cbz_filename(series_name, chapter_number))
            print(f"Creating .cbz file for chapter {chapter_number}...")
            
            with zipfile.ZipFile(cbz_file_path, "w") as cbz_file:
                for series_name, chapter_number, page_number, img_data in image_data_list:
                    screenshot_filename = self.get_screenshot_filename(page_number, cbz_file)
                    cbz_file.writestr(screenshot_filename, img_data)
            
            logger.info(f"Saved chapter {chapter_number} as {cbz_file_path}")
        except Exception as e:
            logger.error(f"Error creating .cbz file for chapter {chapter_number}: {e}")

    def get_series_and_chapter_info(self, image_data_list):
        return image_data_list[0][:2]

    def get_screenshot_filename(self, page_number, cbz_file):
        filename = self.create_screenshot_filename(page_number, len(cbz_file.namelist()))
        if filename in cbz_file.namelist():
            filename = f"{filename.split('.')[0]}_{len(cbz_file.namelist())}.{filename.split('.')[1]}"
            print(f"Image with the same name exists. Renaming to {filename}...")
        return filename


    def download_image(self, img_src):
        try:
            response = requests.get(img_src)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"Error downloading image from {img_src}: {e}")
            return None
    def processing_image(self, img_data):
        try:
            img = Image.open(io.BytesIO(img_data))
            
            # Split image into parts
            if img.height > 1000:
                return self.split_image(img)
            
            # Save image with optimization
            img_byte_array = io.BytesIO()
            img.save(img_byte_array, format="PNG", optimize=True)
            return img_byte_array.getvalue()
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None
  
    def split_image(self, img):
        width, height = img.size
        num_parts = height // 1000 + 1
        part_height = height // num_parts

        # Split the image into parts using a generator expression
        img_parts = (img.crop((0, i*part_height, width, min((i+1)*part_height, height))) 
                    for i in range(num_parts))

        # Convert each part to bytes using a generator expression
        return (self.convert_image_to_bytes(img_part) for img_part in img_parts)
    
    def convert_image_to_bytes(self, img):
        try:
            img_byte_array = io.BytesIO()
            img.save(img_byte_array, format="PNG")
            return img_byte_array.getvalue()
        except Exception as e:
            logger.error(f"Error converting image to bytes: {e}")
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
            self.bulk_save_png_links(self.save_path, page_data)
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
        # Check if a .cbz file already exists for the chapter
        return os.path.exists(os.path.join(self.save_path, self.sanitize_folder_name(series_name), f"{series_name} Chapter {chapter_number}.cbz"))

