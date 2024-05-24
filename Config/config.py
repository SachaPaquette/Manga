import os


class Config:
    ##############################
    #        database.py         #
    #        constants           #
    ##############################
    CONNECTION_STRING = os.environ.get("MONGODB_CONNECTION_STRING") # MongoDB connection string
    DATABASE_LOG_PATH = "./Logs/Database.log" # Path to the log file

    ##############################
    #        mangadownload.py    #
    #        constants           #
    ##############################
    UK_FLAG = 'https://mangadex.org/img/flags/gb.svg' # UK flag URL (used to check if the manga is available in English)
    CHAPTER_CARDS = 'bg-accent.rounded-sm'  # Class name of the chapter cards
    CHAPTER_NUMBER = 'font-bold.self-center.whitespace-nowrap' # Class name of the chapter number
    CHAPTER_LINK = 'chapter-grid.flex-grow'  # Class name of the chapter link
    IMG = 'img'  # Tag name of the image
    LONG_MANGA_PARENT_DIV = "mx-auto.h-full.w-full" # Class name of the parent div of the long manga image
    LONG_MANGA_SUBDIV = "md--page.ls.limit-width.mx-auto" # Class name of the subdiv of the long manga image
    # Class name of the page wrap
    PAGE_WRAP = 'min-w-0.relative.pages-wrap.md--reader-pages'
    NEXT_PAGE_BUTTON = "feather-arrow-right"  # Class name of the next page button
    DEACTIVATED_NEXT_PAGE_BUTTON = "rounded relative md-btn flex items-center px-3 overflow-hidden accent disabled text rounded-full !px-0" # With spaces since the output has spaces
    POP_UP = "md-modal__box.flex-grow"  # Class name of the pop up
    DIV = "div"  # Tag name of the div
    SRC = "src"  # Attribute name of the src
    HREF = "href"  # Attribute name of the href
    HYPERLINK = "a"  # Tag name of the hyperlink
    MANGA_IMAGE = "mx-auto.h-full.md--page.flex" # Class name of the manga image
    LONG_MANGA_IMAGE = "md--page.ls.limit-width.mx-auto" # Class name of the long manga image
    MANGA_DOWNLOAD_LOG_PATH = "./Logs/MangaDownload.log" # Path to the log file
    UNLOADED_SUB_DIV = ".unloaded.mx-auto" # Class name of the unloaded sub div
    # MangaDex search URL (exclude Doujinshi mangas that are fan-made)
    MANGADEX_SEARCH_URL = "https://mangadex.org/titles?q={}&page=1&exclude=b13b2a48-c720-44a9-9c77-39c9979373fb"
    ##############################
    #        mangafetch.py       #
    #        constants           #
    ##############################
    MANGADEX_BASE_URL = "https://mangadex.org/titles?page={}&order=followedCount.desc" # URL to the MangaDex titles page
    TOTAL_PAGES = 313  # Total number of pages to fetch
    MIN_SLEEP_THRESHOLD = 30 # Sleep after every x pages (to avoid getting blocked by MangaDex)
    MAX_SLEEP_THRESHOLD = 40 # Sleep after every x pages (to avoid getting blocked by MangaDex)
    MIN_SLEEP_DURATION = 60  # Minimum sleep duration in seconds
    MAX_SLEEP_DURATION = 120 # Maximum sleep duration in seconds (randomly chosen between min and max)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.48",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.254",
    ]  # List of user agents to rotate through
    MANGA_FETCH_LOG_PATH = "./Logs/MangaFetch.log" # Path to the log file
    
    DEFAULT_SAVE_PATH = "./Manga" # Default save path for the manga (Will be used if no save path is configured in the .env file)
class ScriptConfig:
    windows_script = "./Scripts/windowsinstaller.ps1"
    linux_script = "./Scripts/linuxinstaller.sh"
    requirements_file = "./Requirements/requirements.txt"
    SCRIPT_FILENAME = "installer"
    SCRIPT_LOG_PATH = "./Logs/Installer.log"
    windows_curse = "windows-curses"