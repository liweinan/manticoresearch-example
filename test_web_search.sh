#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to validate JSON response
validate_response() {
    local response="$1"
    local expected_content="$2"
    
    # Check if response is valid JSON
    if ! echo "$response" | jq . >/dev/null 2>&1; then
        echo -e "${RED}❌ Invalid JSON response${NC}"
        return 1
    fi
    
    # Check if response contains error
    if echo "$response" | jq -e '.error' >/dev/null 2>&1; then
        echo -e "${RED}❌ Error in response: $(echo "$response" | jq -r '.error')${NC}"
        return 1
    fi
    
    # Check if response is an array
    if ! echo "$response" | jq -e 'if type=="array" then true else false end' >/dev/null 2>&1; then
        echo -e "${RED}❌ Response is not an array${NC}"
        return 1
    fi
    
    # Check if documents have required fields
    if ! echo "$response" | jq -e 'all(.[]; has("id") and has("title") and has("content_text") and has("weight"))' >/dev/null 2>&1; then
        echo -e "${RED}❌ Documents missing required fields${NC}"
        return 1
    fi

    # Check if expected_content is provided, check if it appears in results
    if [ ! -z "$expected_content" ]; then
        if [[ "$expected_content" == *".*"* ]]; then
            # For mixed language search, check each term separately
            term1=$(echo "$expected_content" | cut -d'.' -f1)
            term2=$(echo "$expected_content" | cut -d'.' -f3)
            if ! echo "$response" | jq -e --arg t1 "$term1" --arg t2 "$term2" 'any(.[].content_text; contains($t1) and contains($t2))' >/dev/null 2>&1; then
                echo -e "${RED}❌ Expected content not found in results: Terms '$term1' and '$term2' not found together${NC}"
                return 1
            fi
        else
            # For regular search, check exact content
            if ! echo "$response" | jq -e --arg content "$expected_content" 'any(.[].content_text; contains($content))' >/dev/null 2>&1; then
                echo -e "${RED}❌ Expected content not found in results: $expected_content${NC}"
                return 1
            fi
        fi
    fi

    # Print success message with result count
    local count=$(echo "$response" | jq length)
    echo -e "${GREEN}✓ Valid response with $count results${NC}"
    
    return 0
}

echo "Starting web search tests..."

# Test Chinese search
echo -e "\n----------------------------------------"
echo "Testing search: Chinese word '测试' (test)"
response=$(curl -s "http://localhost:8080/search?q=测试")
echo "Response:"
echo "$response" | jq .
validate_response "$response" "测试文档"

# Test another Chinese search
echo -e "\n----------------------------------------"
echo "Testing search: Chinese word '中文' (Chinese)"
response=$(curl -s "http://localhost:8080/search?q=中文")
echo "Response:"
echo "$response" | jq .
validate_response "$response" "中文内容"

# Test English search
echo -e "\n----------------------------------------"
echo "Testing search: English word 'test'"
response=$(curl -s "http://localhost:8080/search?q=test")
echo "Response:"
echo "$response" | jq .
validate_response "$response" "test document"

# Test another English search
echo -e "\n----------------------------------------"
echo "Testing search: English word 'english'"
response=$(curl -s "http://localhost:8080/search?q=english")
echo "Response:"
echo "$response" | jq .
validate_response "$response" "English document"

# Test phrase search
echo -e "\n----------------------------------------"
echo "Testing search: English phrase 'search functionality'"
response=$(curl -s "http://localhost:8080/search?q=search%20functionality")
echo "Response:"
echo "$response" | jq .
validate_response "$response" "search functionality"

# Test mixed language search
echo -e "\n----------------------------------------"
echo "Testing search: Mixed Chinese and English search"
response=$(curl -s "http://localhost:8080/search?q=测试%20test")
echo "Response:"
echo "$response" | jq .
validate_response "$response" "测试.*test"

echo -e "\n----------------------------------------"
echo "Web search tests completed." 