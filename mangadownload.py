from dotenv import load_dotenv
from MangaDownload.WebInteractions import WebInteractions
from MangaDownload.MangaOperations import MangaDownloader
from MangaDownload.FileOperations import FileOperations
load_dotenv()

def instantiate_classes():
    web_interactions = WebInteractions() 
    file_operations = FileOperations(web_interactions)
    return MangaDownloader(web_interactions, file_operations)

def main():
    try:
        manga_downloader = instantiate_classes()
        chapters, series_name = manga_downloader.search_and_select_manga() 
        if chapters and series_name:
            for chapter in chapters:
                manga_downloader.print_chapter_info(chapter)
                manga_chapter = chapter['chapter_link'], series_name, chapter['chapter_number']
                manga_downloader.download_images_from_chapter(manga_chapter) 
    except KeyboardInterrupt as e:
        exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        exit()
if __name__ == "__main__":
    main()
    