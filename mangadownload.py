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
    file_operations (FileOperations): An instance of the FileOperations class.
    manga_downloader (MangaDownloader): An instance of the MangaDownloader class.
    """
    web_interactions = WebInteractions()
    file_operations = FileOperations(web_interactions, web_interactions.driver)
    manga_downloader = MangaDownloader(web_interactions, file_operations)
    return web_interactions, file_operations, manga_downloader

def get_manga_chapters_and_name(manga_downloader):
    """
    Search and select a manga.
    """
    return manga_downloader.search_and_select_manga()

def download_chapter_images(manga_downloader, chapter, series_name):
    """
    Download the images from the chapter.
    """
    manga_downloader.download_images_from_chapter(
        chapter['chapter_link'], series_name, chapter['chapter_number']
    )
    
def print_chapter_info(chapter):
    """
    Print the chapter number and name.
    """
    print(f"{chapter['chapter_number']}, {chapter['chapter_name']}, {chapter['chapter_link']}")

def cleanup_resources(web_interactions):
    """
    Clean up the resources used by the program.

    Args:
    web_interactions (WebInteractions): An instance of the WebInteractions class.
    """
    web_interactions.cleanup()
    
    
def main():
    """
    This function is the entry point of the Manga Downloader program. It searches and selects a manga, downloads its images,
    and cleans up the resources used by the program.
    """
    try:
        web_interactions, file_operations, manga_downloader = instantiate_classes() # Instantiate WebInteractions, FileOperations, and MangaDownloader objects
        chapters, series_name = get_manga_chapters_and_name(manga_downloader) # Search and select a manga
        if chapters and series_name:
            for chapter in chapters:
                print_chapter_info(chapter) # Print the chapter number and name
                download_chapter_images(manga_downloader, chapter, series_name) # Download the images from the chapter
        cleanup_resources(web_interactions) # Clean up the resources used by the program
    
        
    except KeyboardInterrupt as e:
        cleanup_resources(web_interactions)
        print("\nQuitting...")
        exit()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        cleanup_resources(web_interactions)

if __name__ == "__main__":
    main() # Run the main function
