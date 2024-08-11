
class Config:
    CHAPTER_CARDS = 'bg-accent.rounded-sm'  # Class name of the chapter cards
    CHAPTER_LINK = 'chapter-grid.flex-grow'  # Class name of the chapter link
    IMG = 'img'  # Tag name of the image
    PAGE_WRAP = 'min-w-0.relative.pages-wrap.md--reader-pages' # Class name of the page wrap
    NEXT_PAGE_BUTTON = "feather-arrow-right"  # Class name of the next page button
    DEACTIVATED_NEXT_PAGE_BUTTON = "rounded relative md-btn flex items-center px-3 overflow-hidden accent disabled text rounded-full !px-0" # With spaces since the output has spaces
    DIV = "div"  # Tag name of the div
    SRC = "src"  # Attribute name of the src
    HREF = "href"  # Attribute name of the href
    HYPERLINK = "a"  # Tag name of the hyperlink
    MANGA_DOWNLOAD_LOG_PATH = "./Logs/MangaDownload.log" # Path to the log file
    MANGADEX_SEARCH_URL = "https://mangadex.org/titles?q={}&page=1&exclude=b13b2a48-c720-44a9-9c77-39c9979373fb"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.48",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.254",
    ]  # List of user agents to rotate through
    DEFAULT_SAVE_PATH = "./Mangas" # Default save path for the manga (Will be used if no save path is configured in the .env file)
    CRX_PATH = "Extensions/uBlock-Origin.crx"
class ScriptConfig:
    windows_script = "./Scripts/windowsinstaller.ps1"
    linux_script = "./Scripts/linuxinstaller.sh"
    requirements_file = "./Requirements/requirements.txt"
    SCRIPT_FILENAME = "installer"
    SCRIPT_LOG_PATH = "./Logs/Installer.log"
    windows_curse = "windows-curses"