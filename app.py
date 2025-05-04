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
    'user': '',             # No authentication required
    'password': '',         # No password required
    'raise_on_warnings': True,                           # Raise exceptions on warnings
    'charset': 'utf8mb4',                               # Use UTF-8 encoding
    'use_unicode': True                                 # Enable Unicode support
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
    return None


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
app.config['JSON_AS_ASCII'] = False  # Ensure proper UTF-8 encoding for JSON responses
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'  # Set proper MIME type

# Disable HTML error pages
@app.errorhandler(Exception)
def handle_error(error):
    response = jsonify({
        'error': True,
        'message': str(error)
    })
    response.status_code = 500
    return response

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
    """
    try:
        # Get query from either GET parameters or POST JSON
        if request.method == 'GET':
            query = request.args.get('q', '', type=str)
            logger.debug(f"GET request received with query: {query}")
            # Handle URL-encoded UTF-8
            query = query.encode('latin1').decode('utf-8')
        else:
            query = request.json.get('q', '')
            logger.debug(f"POST request received with query: {query}")
        
        # Log the received query in detail
        logger.debug(f"Query details:")
        logger.debug(f"- Type: {type(query)}")
        logger.debug(f"- Length: {len(query)}")
        logger.debug(f"- Bytes: {query.encode('utf-8')}")
        # Check if query contains Chinese characters
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in query)
        logger.debug(f"- Is Chinese: {is_chinese}")
        
        # Connect to Manticore
        logger.debug("Attempting to connect to Manticore...")
        connection = mysql.connector.connect(**MANTICORE_PARAMS)
        logger.debug("Successfully connected to Manticore")
        
        cursor = connection.cursor(dictionary=True)
        
        # Tokenize the query
        logger.debug("Starting Jieba tokenization...")
        tokens = list(jieba.cut(query))
        logger.debug(f"Jieba tokens: {tokens}")
        
        # Process tokens
        search_terms = []
        for token in tokens:
            if not token.strip():
                continue
            logger.debug(f"Processing token: {token}")
            logger.debug(f"- Token bytes: {token.encode('utf-8')}")
            logger.debug(f"- Token length: {len(token)}")
            search_terms.append(f'"{token}"')
        
        search_query = ' '.join(search_terms)
        logger.debug(f"Final search query: {search_query}")
        
        # Execute search
        sql = """
        SELECT id, title, content, WEIGHT() as weight 
        FROM documents_idx 
        WHERE MATCH(%s)
        ORDER BY weight DESC
        LIMIT 10
        """
        
        logger.debug(f"Executing SQL query: {sql % search_query}")
        try:
            cursor.execute(sql, (search_query,))
            logger.debug("SQL query executed successfully")
        except Exception as e:
            logger.error(f"SQL query execution failed: {str(e)}")
            logger.error(f"Query that failed: {sql % search_query}")
            return jsonify({
                'error': True,
                'message': f"SQL query execution failed: {str(e)}",
                'query': query
            }), 500
        
        results = cursor.fetchall()
        logger.debug(f"Found {len(results)} results")
        
        # Process results
        processed_results = []
        for result in results:
            try:
                logger.debug(f"Processing result: {result['id']}")
                content_json = json.loads(result['content'])
                processed_result = {
                    'id': result['id'],
                    'title': result['title'],
                    'content': content_json.get('text', ''),
                    'tags': content_json.get('tags', []),
                    'weight': result['weight']
                }
                processed_results.append(processed_result)
                logger.debug(f"Successfully processed result {result['id']}")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing content JSON: {str(e)}")
                logger.error(f"Raw content: {result['content']}")
                processed_result = {
                    'id': result['id'],
                    'title': result['title'],
                    'content': result['content'],
                    'tags': [],
                    'weight': result['weight']
                }
                processed_results.append(processed_result)
        
        # Close connections
        cursor.close()
        connection.close()
        
        # Return results
        logger.debug(f"Returning {len(processed_results)} processed results")
        return jsonify(processed_results)
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return jsonify({
            'error': True,
            'message': str(e),
            'query': query
        }), 500

if __name__ == '__main__':
    # Initialize database and start the Flask application
    init_db()
    app.run(host='0.0.0.0', port=5000) 