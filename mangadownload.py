# Description: This script downloads manga from mangadex.org and saves it to the local disk.
import os
from dotenv import load_dotenv
from config import Config
from logs_config import setup_logging
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.MangaOperations import MangaDownloader
from MangaDownload.FileOperations import FileOperations
# Load environment variables from .env file
load_dotenv()


# Set up logging to a file

def main():
    try:
        # Instantiate WebInteractions, FileOperations, and MangaDownloader
            
        web_interactions = WebInteractions()
        file_operations = FileOperations(web_interactions)
        manga_downloader = MangaDownloader(web_interactions, file_operations)
        # Search and select a manga
        chapters, series_name = manga_downloader.search_and_select_manga()
        if chapters and series_name:
            # Once you have the chapters, you can loop through them and download images
            for chapter in chapters:
                print(
                    f"{chapter['chapter_number']}, {chapter['chapter_name']}")
                manga_downloader.download_images_from_chapter(
                    chapter['chapter_link'], series_name, chapter['chapter_number']
                )
        web_interactions.cleanup()
    except KeyboardInterrupt as e:
        print("\nQuitting...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
