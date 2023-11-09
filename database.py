import csv
import os
import pandas as pd
import pymongo
from dotenv import load_dotenv
import re
from Config.config import Config
from Config.logs_config import setup_logging
# Load environment variables from .env file
load_dotenv()

# Set up logging to a file
logger = setup_logging('database', Config.DATABASE_LOG_PATH)


def connect_db(database_name, collection_name):
    """Function to connect to a MongoDB database and return the collection object

    Args:
        database_name (string): The name of the database
        collection_name (string): The name of the collection

    Returns:
        pymongo.collection.Collection: The MongoDB collection object
    """
    try:
        client = pymongo.MongoClient(
            Config.CONNECTION_STRING)  # Connect to MongoDB
        db = client[database_name]  # Connect to the "Manga" database
        # Connect to the "Collection" collection
        collection = db[collection_name]
        return collection
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise  # Re-raise the exception to stop further execution


def connect_collection_db():
    """Function to connect to the MongoDB collection and return the collection object

    Returns:
        pymongo.collection.Collection: The MongoDB collection object
    """
    # Connect to the "Manga" database and "Collection" collection
    return connect_db("Manga", "Collection")


def create_index(collection):
    """Function to create an index on the 'title' field for better performance
    

    Args:
        collection (pymongo.collection.Collection): The MongoDB collection
    """
    # Create an index on the 'title' field
    collection.create_index([('title', pymongo.ASCENDING)])


def insert_to_db(collection, data):
    """Function to insert data into a MongoDB collection

    Args:
        collection (pymongo.collection.Collection): The MongoDB collection
        data (list): The data to insert
    """
    try:
        # Insert the data into the MongoDB collection
        collection.insert_many(data)
    except pymongo.errors.DuplicateKeyError as e:
        logger.error(f"Error inserting data to MongoDB: {e}")
        raise  # Re-raise the exception to stop further execution
    except pymongo.errors.BulkWriteError as bwe:
        # Handle specific MongoDB write errors
        logger.error(f"MongoDB Bulk Write Error: {bwe.details}")
        raise
    except Exception as e:
        logger.error(f"Error inserting data into MongoDB collection: {e}")
        raise


def insert_manga_to_db(data):
    """Function to insert manga data such as the title, description and link into the MongoDB collection, using the insert_to_db function defined above

    Args:
        data (list): The manga's information to insert
    """
    if data:
        # Connect to the "Manga" database and "Collection" collection and insert the data
        insert_to_db(connect_collection_db(), data)
    else:
        logger.info("No data to insert")

def delete_duplicates(collection, duplicates_cursor):
    """
    Deletes extra occurrences of duplicate documents in a MongoDB collection.

    Args:
        collection (pymongo.collection.Collection): The MongoDB collection to remove duplicates from.
        duplicates_cursor (pymongo.command_cursor.CommandCursor): The cursor containing the duplicate documents.

    Returns:
        None
    """
    # Iterate over the duplicate documents and remove extra occurrences
    for duplicate_group in duplicates_cursor:
        # Get the extra occurrences
        extra_occurrences = duplicate_group['ids'][1:]
        # Delete the extra occurrences
        collection.delete_many({'_id': {'$in': extra_occurrences}})
def detect_duplicates():
    """
    Detect and remove duplicate documents in the MongoDB collection.

    This function connects to the "Manga" database and "Collection" collection,
    creates an index on the 'title' field for better performance, and uses a
    MongoDB aggregation pipeline to find and remove duplicates.

    Returns:
        None.

    Raises:
        pymongo.errors.PyMongoError: If there is an error while connecting to
            the database or executing the aggregation pipeline.
    """
    # Connect to the "Manga" database and "Collection" collection
    collection = connect_collection_db()

    # Create an index on the 'title' field for better performance
    create_index(collection)

    # MongoDB aggregation pipeline to find and remove duplicates
    duplicates_pipeline = [
        {
            '$group': {
                '_id': '$title',
                'count': {
                    '$sum': 1
                },
                'ids': {'$push': '$_id'}
            }
        }, {
            '$match': {
                'count': {
                    '$gt': 1
                }
            }
        }
    ]

    # Find all the duplicate documents
    duplicates_cursor = collection.aggregate(duplicates_pipeline)
    # Remove the duplicate documents
    delete_duplicates(collection, duplicates_cursor)


    print('Duplicates are now removed :)')


def fetch_mangas():
    """
    Fetches all the manga documents from the "Collection" collection in the "Manga" database.

    Returns:
    mangas (pymongo.cursor.Cursor): A cursor object containing all the manga documents.
    """
    # Connect to the "Manga" database and "Collection" collection
    collection = connect_collection_db()
    # Find all the documents in the collection
    mangas = collection.find(
        {}, {'_id': 0, 'title': 1, 'link': 1, 'status': 1, 'desc': 1})
    return mangas
import re

def create_regex_pattern(input):
    """
    Creates a regular expression pattern that matches any string containing the given input, ignoring case.

    Args:
        input (str): The input string to match.

    Returns:
        A compiled regular expression pattern object.
    """
    return re.compile(f".*{re.escape(input)}.*", re.IGNORECASE)

def find_mangas(input):
    """
    Finds mangas in the "Manga" database that match the given input.

    Args:
        input (str): The input string to match against the manga titles.

    Returns:
        list: A list of dictionaries containing the matching manga documents. Each dictionary contains the title, link, status, and desc fields.
        None: If an error occurs during the database query, returns None.
    """
    try:
        # Create a regex pattern for matching substrings of the input
        pattern = create_regex_pattern(input)

        # Connect to the "Manga" database and "Collection" collection
        collection = connect_collection_db()

        # Use the regex pattern in the query to find matching documents and return only the title, link, status and desc fields
        mangas_cursor = collection.find(
            {'title': {'$regex': pattern}},
            {'_id': 0, 'title': 1, 'link': 1, 'status': 1, 'desc': 1}
        )

        # Convert the cursor to a list
        mangas = list(mangas_cursor)

        return mangas  # Return the list of matching documents
    except Exception as e:
        logger.error(f"Error in find_mangas: {e}")
        return None


def remove_doujinshi():
    """
    Removes all entries from the "Manga" database's "Collection" collection that have a title
    including the word "doujinshi". Doujinshi is a genre of manga that is fan-made and not officially
    published, and will not be downloaded by this program.

    Returns:
        None
    """
    try:
        # Connect to the "Manga" database and "Collection" collection
        collection = connect_collection_db()

        # Find all titles including "doujinshi"
        doujinshi_entries = collection.find(
            {'title': re.compile(r'doujinshi', re.IGNORECASE)},
            {'_id': 0, 'title': 1}
        )

        # Extract titles from the result
        titles_to_remove = [entry['title'] for entry in doujinshi_entries]

        # Delete all entries with titles including "doujinshi"
        collection.delete_many({'title': {'$in': titles_to_remove}})

        logger.info(
            f"Deleted {len(titles_to_remove)} entries with 'doujinshi' genre.")
    except Exception as e:
        logger.error(f"Error in remove_doujinshi: {e}")
