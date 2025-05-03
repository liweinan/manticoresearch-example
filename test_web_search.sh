#!/bin/bash

# Function to perform a search and display results
perform_search() {
    local query="$1"
    local description="$2"
    
    echo "Testing search: $description"
    echo "Query: $query"
    
    echo "Response:"
    response=$(curl -s -X POST "http://localhost:8080/search" \
         -H "Content-Type: application/json" \
         -d "{\"query\": \"$query\"}")
    
    if [ $? -eq 0 ]; then
        # Use Python to pretty print JSON with proper Unicode handling
        echo "$response" | python3 -c '
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data, ensure_ascii=False, indent=2))
'
    else
        echo "Error: Failed to get response"
        echo "$response"
    fi
    
    echo -e "\n----------------------------------------\n"
}

echo "Starting web search tests..."
echo -e "----------------------------------------\n"

# Test Chinese searches
perform_search "测试" "Chinese word '测试'"
perform_search "中文" "Chinese word '中文'"

# Test English searches
perform_search "test" "English word 'test'"
perform_search "english" "English word 'english'"
perform_search "search functionality" "English phrase 'search functionality'"

# Test mixed language document
perform_search "测试 test" "Mixed Chinese and English search"

echo "Web search tests completed." 