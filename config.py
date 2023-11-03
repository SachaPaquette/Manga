class Config:
    # mangadownload.py
    UK_FLAG = 'https://mangadex.org/img/flags/gb.svg' # UK flag URL (used to check if the manga is available in English)
    CHAPTER_CARDS = 'bg-accent.rounded-sm' # Class name of the chapter cards
    CHAPTER_NUMBER = 'font-bold.self-center.whitespace-nowrap' # Class name of the chapter number
    CHAPTER_LINK = 'chapter-grid.flex-grow' # Class name of the chapter link
    IMG = 'img' # Tag name of the image
    PAGE_WRAP = 'min-w-0.relative.pages-wrap.md--reader-pages' # Class name of the page wrap
    NEXT_PAGE_BUTTON = "feather-arrow-right" # Class name of the next page button
    # With spaces since the output has spaces
    DEACTIVATED_NEXT_PAGE_BUTTON = "rounded relative md-btn flex items-center px-3 overflow-hidden accent disabled text rounded-full !px-0"
    POP_UP = "md-modal__box.flex-grow" # Class name of the pop up
    DIV = "div" # Tag name of the div
    SRC = "src" # Attribute name of the src
    HREF = "href" # Attribute name of the href
    HYPERLINK = "a" # Tag name of the hyperlink
    MANGA_IMAGE = "mx-auto.h-full.md--page.flex"
    LONG_MANGA_IMAGE = "md--page.ls.limit-width.mx-auto"
    
    
    # mangafetch.py
    MANGADEX_BASE_URL = "https://mangadex.org/titles?page={}&order=followedCount.desc" # URL to the MangaDex titles page
    TOTAL_PAGES = 313 # Total number of pages to fetch
    MIN_SLEEP_THRESHOLD = 30 
    MAX_SLEEP_THRESHOLD = 40 # Sleep after every x pages (to avoid getting blocked by MangaDex)
    MIN_SLEEP_DURATION = 60  # Minimum sleep duration in seconds
    MAX_SLEEP_DURATION = 120  # Maximum sleep duration in seconds (randomly chosen between min and max)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.48",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.254",
    ]