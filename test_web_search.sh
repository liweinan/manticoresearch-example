#!/bin/bash

# This script tests the web search API functionality
# It demonstrates how to use the search endpoint with different types of queries:
# - Chinese text searches
# - English text searches
# - Mixed language searches
# The script uses curl to make HTTP requests and Python to format the JSON output

# Function to perform a search and display results
perform_search() {
    local query="$1"        # The search query to test
    local description="$2"  # Description of what we're testing
    
    echo "Testing search: $description"
    echo "Query: $query"
    
    echo "Response:"
    # Make a POST request to the search endpoint
    # -s: silent mode (no progress meter)
    # -X POST: use POST method
    # -H: set Content-Type header to JSON
    # -d: send JSON data in the request body
    response=$(curl -s -X POST "http://localhost:8080/search" \
         -H "Content-Type: application/json" \
         -d "{\"query\": \"$query\"}")
    
    if [ $? -eq 0 ]; then
        # Use Python to pretty print JSON with proper Unicode handling
        # This ensures Chinese characters are displayed correctly
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
# These tests verify Chinese character handling and word segmentation
perform_search "测试" "Chinese word '测试' (test)"
perform_search "中文" "Chinese word '中文' (Chinese)"

# Test English searches
# These tests verify English text search functionality
perform_search "test" "English word 'test'"
perform_search "english" "English word 'english'"
perform_search "search functionality" "English phrase 'search functionality'"

# Test mixed language search
# This test verifies handling of queries containing both Chinese and English
perform_search "测试 test" "Mixed Chinese and English search"

echo "Web search tests completed." 