# Manga Downloader

Manga Downloader is a Python script designed for downloading manga chapters from MangaDex. The script utilizes Selenium for web scraping to fetch manga chapters and images.

## Prerequisites

Make sure you have the following installed:

- Python 3
- Chrome Browser
- ChromeDriver (automatically managed by ChromeDriverManager)
- MongoDB

## Usage

1. **Clone the repository:**

    ```bash
    git clone https://github.com/SachaPaquette/Manga.git
    ```

2. **Navigate to the project directory:**

    ```bash
    cd Manga/
    ```

3. **Install the required Python packages:**

    ```bash
    pip install -r Requirements\requirements.txt
    ```

4. **Configuration:**

    Create a `.env` file in the project root and add the following environment variables:

    ```env
    MONGODB_CONNECTION_STRING = "YOUR_MONGODB_CONNECTION"
    SAVE_PATH=/path/to/save/manga
    ```

    Replace `/path/to/save/manga` with the desired path to save manga images.
    Replace `YOUR_MONGODB_CONNECTION` with your MongoDB connection string.

5. **Run the scripts:**

    ```bash
    python mangafetch.py
    ```
    - Enter "Y" to start fetching the manga names and inserting them into your database.

    ```bash
    python mangadownload.py
    ```
    - Enter the name of the manga when prompted.
    - Select the manga from the search results.
    - Wait for the chapters to be fetched and created.

6. The script will fetch and download all chapters for the selected manga.

7. After downloading manga chapters, the script will automatically clean up resources and close the browser.


8. After downloading manga chapters, the script will automatically clean up resources and close the browser.
