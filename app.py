"""
Multilingual Search Application with Manticore Search

This Flask application provides a multilingual search interface that supports both Chinese and English text.
It uses:
- PostgreSQL for data storage
- Manticore Search for full-text search capabilities
- Jieba for Chinese word segmentation
- Flask for the web interface

The application demonstrates:
1. Integration of multiple services (PostgreSQL, Manticore Search)
2. Chinese text processing with Jieba
3. JSONB data handling in PostgreSQL
4. RESTful API implementation
5. Error handling and logging
"""

import os
import time
import json
import psycopg2
import mysql.connector
import jieba
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
# This allows configuration without hardcoding sensitive information
load_dotenv()

# Initialize Jieba with the large dictionary for better Chinese word segmentation
# The dictionary contains more words and better handles complex Chinese characters
jieba.set_dictionary('data/dict.txt.big')

# Database connection parameters for PostgreSQL
# These can be overridden by environment variables for flexibility
DB_PARAMS = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),      # PostgreSQL host
    'user': os.getenv('POSTGRES_USER', 'postgres'),      # Database user
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),  # Database password
    'dbname': os.getenv('POSTGRES_DB', 'search_db'),     # Database name
    'port': 5432                                         # PostgreSQL port
}

# Manticore Search connection parameters
MANTICORE_PARAMS = {
    'host': os.getenv('MANTICORE_HOST', 'manticore'),    # Manticore Search host
    'port': int(os.getenv('MANTICORE_PORT', '9306')),    # MySQL protocol port
    'user': os.getenv('MANTICORE_USER', ''),             # No authentication required
    'password': os.getenv('MANTICORE_PASSWORD', ''),      # No password required
    'database': os.getenv('MANTICORE_DATABASE', ''),     # No specific database required
    'use_pure': True,                                    # Use pure Python implementation
    'raise_on_warnings': True                           # Raise exceptions on warnings
}

# Configure logging with detailed format
# This will show timestamp, logger name, log level, and message
logging.basicConfig(
    level=logging.DEBUG,  # Show all log levels (DEBUG and above)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Create a logger instance for this module
logger = logging.getLogger(__name__)

def wait_for_postgres(max_retries=10, delay=10):
    """
    Wait for PostgreSQL to be ready before proceeding.
    
    This is important in Docker environments where services might start in different orders.
    The function will:
    1. Try to connect to PostgreSQL
    2. If successful, return True
    3. If failed, wait and retry up to max_retries times
    4. If all retries fail, return False
    
    Args:
        max_retries (int): Maximum number of connection attempts
        delay (int): Seconds to wait between retries
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    retries = 0
    while retries < max_retries:
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            conn.close()
            print("Successfully connected to PostgreSQL")
            return True
        except psycopg2.OperationalError as e:
            retries += 1
            if retries < max_retries:
                print(f"Waiting for PostgreSQL... (attempt {retries}/{max_retries})")
                print(f"Error: {e}")
                time.sleep(delay)
            else:
                print("Failed to connect to PostgreSQL after maximum retries")
                print(f"Last error: {e}")
                return False

def init_db():
    """
    Initialize the database with sample data.
    
    This function:
    1. Creates the documents table if it doesn't exist
    2. Clears any existing data
    3. Inserts sample documents with mixed Chinese and English content
    4. Each document has a title and JSONB content containing text and tags
    
    The sample data demonstrates:
    - Chinese text handling
    - English text handling
    - Mixed language content
    - JSONB data structure
    - Tag-based categorization
    """
    if not wait_for_postgres():
        return

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # Create table if it doesn't exist
    # The content field uses JSONB for flexible document structure
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content JSONB
        )
    """)

    # Clear existing data and reset the sequence
    cur.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE")

    # Sample data demonstrating various search scenarios
    sample_data = [
        # Document with Chinese text and mixed tags
        ("文档1", {"text": "这是一个测试文档，包含一些中文内容。This is a test document with some Chinese content.", "tags": ["测试", "中文", "test"]}),
        # Document with Chinese text and mixed tags
        ("文档2", {"text": "这是另一个文档，也包含中文内容。Another document with Chinese content.", "tags": ["示例", "中文", "example"]}),
        # Document with Chinese text and mixed tags
        ("文档3", {"text": "第三个文档，同样包含中文内容。The third document also contains Chinese content.", "tags": ["测试", "示例", "third"]}),
        # Pure English document
        ("Document 4", {"text": "This is a pure English document for testing search functionality.", "tags": ["english", "test"]}),
        # Pure English document
        ("Document 5", {"text": "Another English document to verify search capabilities.", "tags": ["english", "verify"]})
    ]

    # Insert each document into the database
    for title, content in sample_data:
        cur.execute(
            "INSERT INTO documents (title, content) VALUES (%s, %s)",
            (title, json.dumps(content))
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized with sample data")

# Initialize Flask application
app = Flask(__name__)

@app.route('/')
def index():
    """
    Render the main search page.
    
    Returns:
        str: Rendered HTML template
    """
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Handle search requests with detailed logging.
    
    This endpoint:
    1. Accepts both GET and POST requests
    2. Processes queries in both Chinese and English
    3. Uses Jieba for Chinese word segmentation
    4. Searches using Manticore Search
    5. Returns results in JSON format
    
    Logging is added at key points to track:
    - Query reception
    - Connection status
    - Tokenization results
    - SQL query execution
    - Result count
    - Any errors that occur
    """
    # Get query from either GET parameters or POST JSON
    if request.method == 'GET':
        query = request.args.get('q', '')
    else:
        query = request.json.get('q', '')
    
    # Log the received query
    logger.debug(f"Received search query: {query}")
    
    try:
        # Log connection parameters (without password)
        logger.debug(f"Connecting to Manticore with params: { {k:v for k,v in MANTICORE_PARAMS.items() if k != 'password'} }")
        
        # Connect to Manticore Search using the configured parameters
        connection = mysql.connector.connect(**MANTICORE_PARAMS)
        logger.debug("Connected to Manticore")
        
        cursor = connection.cursor(dictionary=True)
        
        # Tokenize the query using Jieba
        tokens = jieba.cut(query)
        search_terms = ' '.join(tokens)
        logger.debug(f"Tokenized query: {search_terms}")
        
        # Build and execute the search query
        sql = """
        SELECT id, title, content_text, WEIGHT() as weight 
        FROM documents_idx 
        WHERE MATCH(%s)
        ORDER BY weight DESC
        LIMIT 10
        """
        
        logger.debug(f"Executing SQL query: {sql % search_terms}")
        cursor.execute(sql, (search_terms,))
        
        results = cursor.fetchall()
        logger.debug(f"Found {len(results)} results")
        
        cursor.close()
        connection.close()
        
        return jsonify(results)
        
    except mysql.connector.Error as e:
        # Log MySQL-specific errors with more detail
        logger.error(f"MySQL Error during search: {str(e)}", exc_info=True)
        return jsonify({'error': f"Database error: {str(e)}"}), 500
    except Exception as e:
        # Log other errors with full stack trace
        logger.error(f"Error during search: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database and start the Flask application
    init_db()
    app.run(host='0.0.0.0', port=5000) 