import csv
import os
import pandas as pd
import pymongo
from dotenv import load_dotenv
import re
from config import Config
from logs_config import setup_logging
# Load environment variables from .env file
load_dotenv()

# Set up logging to a file
logger = setup_logging('database', Config.DATABASE_LOG_PATH)


def connect_db(database_name, collection_name):
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
    # Connect to the "Manga" database and "Collection" collection
    return connect_db("Manga", "Collection")


def create_index(collection):
    # Create an index on the 'title' field
    # Create an index on the 'title' field
    collection.create_index([('title', pymongo.ASCENDING)])


def insert_to_db(collection, data):
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
    if data:
        # Connect to the "Manga" database and "Collection" collection and insert the data
        insert_to_db(connect_collection_db(), data)
    else:
        logger.info("No data to insert")


def detect_duplicates():
    print('detecting duplicates')

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

    # Iterate over the duplicate documents and remove extra occurrences
    for duplicate_group in duplicates_cursor:
        # Get the extra occurrences
        extra_occurrences = duplicate_group['ids'][1:]
        # Delete the extra occurrences
        collection.delete_many({'_id': {'$in': extra_occurrences}})

    print('duplicates removed')


def fetch_mangas():
    # Connect to the "Manga" database and "Collection" collection
    collection = connect_collection_db()
    # Find all the documents in the collection
    mangas = collection.find(
        {}, {'_id': 0, 'title': 1, 'link': 1, 'status': 1, 'desc': 1})
    return mangas


def find_mangas(input):
    try:
        # Create a regex pattern for matching substrings of the input
        pattern = re.compile(f".*{re.escape(input)}.*", re.IGNORECASE)

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
    # Doujinshi is a genre of manga that is fan-made and not officially published
    # We WILL NOT be downloading doujinshis

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

        print(
            f"Deleted {len(titles_to_remove)} entries with 'doujinshi' genre.")
        logger.info(
            f"Deleted {len(titles_to_remove)} entries with 'doujinshi' genre.")
    except Exception as e:
        logger.error(f"Error in remove_doujinshi: {e}")
