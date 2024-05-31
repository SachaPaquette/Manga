# Description: This script downloads manga from mangadex.org and saves it to the local disk.
from dotenv import load_dotenv
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.MangaOperations import MangaDownloader
from MangaDownload.FileOperations import FileOperations
# Load environment variables from .env file
load_dotenv()

def instantiate_classes():
    """
    Instantiate WebInteractions, FileOperations, and MangaDownloader objects.

    Returns:
    web_interactions (WebInteractions): An instance of the WebInteractions class.
    manga_downloader (MangaDownloader): An instance of the MangaDownloader class.
    """
    return WebInteractions(), MangaDownloader(WebInteractions(), FileOperations(WebInteractions()))

def main():
    """
    This function is the entry point of the Manga Downloader program. It searches and selects a manga, downloads its images,
    and cleans up the resources used by the program.
    """
    try:
        web_interactions, manga_downloader = instantiate_classes() # Instantiate WebInteractions, FileOperations, and MangaDownloader objects
        chapters, series_name = manga_downloader.search_and_select_manga()
        if chapters and series_name:
            for chapter in chapters:
                manga_downloader.print_chapter_info(chapter) # Print the chapter number and name
                manga_downloader.download_images_from_chapter(chapter['chapter_link'], series_name, chapter['chapter_number'])   
    except KeyboardInterrupt as e:
        exit()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        web_interactions.cleanup()
        exit()
if __name__ == "__main__":
    main() # Run the main function
