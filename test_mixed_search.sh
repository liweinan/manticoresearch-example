#!/bin/bash

echo "Testing search with Chinese characters '测试':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text FROM documents_idx WHERE MATCH('测试')"

echo -e "\nTesting search with Chinese characters '中文':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text FROM documents_idx WHERE MATCH('中文')"

echo -e "\nTesting search with English word 'test':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text FROM documents_idx WHERE MATCH('test')"

echo -e "\nTesting search with English word 'english':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text FROM documents_idx WHERE MATCH('english')"

echo -e "\nTesting search with English phrase 'search functionality':"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text FROM documents_idx WHERE MATCH('search functionality')"

echo -e "\nShowing all documents in the index:"
docker-compose exec manticore mysql -h0 -P9306 -e "SELECT id, title, content_text FROM documents_idx" 