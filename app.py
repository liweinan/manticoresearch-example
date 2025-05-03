import os
import time
import json
import psycopg2
import mysql.connector
import jieba
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Jieba with dictionary
jieba.set_dictionary('data/dict.txt.big')

# Database connection parameters
DB_PARAMS = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'dbname': os.getenv('POSTGRES_DB', 'search_db'),
    'port': 5432
}

# Manticore Search connection parameters
MANTICORE_PARAMS = {
    'host': os.getenv('MANTICORE_HOST', 'manticore'),
    'port': 9306,
    'user': '',
    'password': '',
    'database': ''
}

def wait_for_postgres(max_retries=10, delay=10):
    """Wait for PostgreSQL to be ready."""
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
    """Initialize the database with sample data."""
    if not wait_for_postgres():
        return

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content JSONB
        )
    """)

    # Insert sample data with mixed Chinese and English text
    sample_data = [
        ("文档1", {"text": "这是一个测试文档，包含一些中文内容。This is a test document with some Chinese content.", "tags": ["测试", "中文", "test"]}),
        ("文档2", {"text": "这是另一个文档，也包含中文内容。Another document with Chinese content.", "tags": ["示例", "中文", "example"]}),
        ("文档3", {"text": "第三个文档，同样包含中文内容。The third document also contains Chinese content.", "tags": ["测试", "示例", "third"]}),
        ("Document 4", {"text": "This is a pure English document for testing search functionality.", "tags": ["english", "test"]}),
        ("Document 5", {"text": "Another English document to verify search capabilities.", "tags": ["english", "verify"]})
    ]

    for title, content in sample_data:
        cur.execute(
            "INSERT INTO documents (title, content) VALUES (%s, %s)",
            (title, json.dumps(content))
        )

    conn.commit()
    cur.close()
    conn.close()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        data = request.get_json()
        query = data.get('query', '')
    else:
        query = request.args.get('q', '')

    if not query:
        return jsonify([])

    # Tokenize the query using Jieba
    tokens = list(jieba.cut(query))
    search_query = ' '.join(tokens)

    # Connect to Manticore Search
    conn = mysql.connector.connect(**MANTICORE_PARAMS)
    cursor = conn.cursor(dictionary=True)

    # Execute search query
    cursor.execute(f"""
        SELECT id, title, content_text
        FROM documents_idx
        WHERE MATCH('{search_query}')
        LIMIT 10
    """)

    results = []
    for row in cursor:
        results.append({
            'id': row['id'],
            'title': row['title'],
            'content': row['content_text']
        })

    cursor.close()
    conn.close()

    return jsonify(results)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000) 