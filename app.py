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
# Manticore Search provides both MySQL and HTTP interfaces
MANTICORE_PARAMS = {
    'host': os.getenv('MANTICORE_HOST', 'manticore'),    # Manticore Search host
    'port': 9306,                                        # MySQL protocol port
    'user': '',                                          # No authentication required
    'password': '',                                      # No password required
    'database': ''                                       # No specific database required
}

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
    Handle search requests.
    
    This endpoint:
    1. Accepts both GET and POST requests
    2. Processes queries in both Chinese and English
    3. Uses Jieba for Chinese word segmentation
    4. Searches using Manticore Search
    5. Returns results in JSON format
    
    The function demonstrates:
    - URL parameter handling
    - JSON request handling
    - Chinese text processing
    - Database querying
    - Error handling
    - Response formatting
    
    Returns:
        JSON: Search results or error message
    """
    try:
        # Get query from either POST JSON or GET parameter
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('query', '')
        else:
            query = request.args.get('q', '')
            # Decode URL-encoded query for Chinese characters
            query = query.encode('latin1').decode('utf-8')

        if not query:
            return jsonify([])

        # Tokenize the query using Jieba for Chinese text
        # This splits Chinese text into meaningful words
        tokens = list(jieba.cut(query))
        search_query = ' '.join(tokens)

        # Connect to Manticore Search using MySQL protocol
        conn = mysql.connector.connect(**MANTICORE_PARAMS)
        cursor = conn.cursor(dictionary=True)

        # Execute search query with proper escaping to prevent SQL injection
        safe_query = search_query.replace("'", "''")
        query_sql = f"""
            SELECT id, title, content_text, content_json
            FROM documents_idx
            WHERE MATCH(%s)
            LIMIT 10
        """
        cursor.execute(query_sql, (safe_query,))

        # Process and format results
        results = []
        for row in cursor:
            try:
                # Parse the JSON content and combine with text
                content_json = json.loads(row['content_json'])
                content_data = {
                    'text': row['content_text'],
                    'tags': content_json.get('tags', [])
                }
                results.append({
                    'id': row['id'],
                    'title': row['title'],
                    'content': content_data
                })
            except Exception as e:
                print(f"Error processing row: {e}")
                print(f"Row data: {row}")
                continue

        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Initialize database and start the Flask application
    init_db()
    app.run(host='0.0.0.0', port=5000) 