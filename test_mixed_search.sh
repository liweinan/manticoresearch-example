#!/bin/bash

# This script tests the Manticore Search functionality directly
# It bypasses the web API and connects to Manticore Search using the MySQL protocol
# The tests verify that the search engine correctly indexes and searches:
# - Chinese text
# - English text
# - Mixed language content

# Test Chinese character search
# This verifies that Manticore Search can handle and search Chinese text
echo "Testing search with Chinese characters '测试' (test):"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text, content_json FROM documents_idx WHERE MATCH('测试')"

# Test another Chinese character search
echo -e "\nTesting search with Chinese characters '中文' (Chinese):"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text, content_json FROM documents_idx WHERE MATCH('中文')"

# Test English word search
echo -e "\nTesting search with English word 'test':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text, content_json FROM documents_idx WHERE MATCH('test')"

# Test another English word search
echo -e "\nTesting search with English word 'english':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text, content_json FROM documents_idx WHERE MATCH('english')"

# Test English phrase search
echo -e "\nTesting search with English phrase 'search functionality':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text, content_json FROM documents_idx WHERE MATCH('search functionality')"

# Display all documents in the index
# This helps verify the data structure and content
echo -e "\nShowing all documents in the index:"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text, content_json FROM documents_idx" 