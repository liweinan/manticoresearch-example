#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color
YELLOW='\033[1;33m'
BLUE='\033[0;34m'

# Detect if running in CI environment
if [ -n "$CI" ]; then
    echo "Running in CI environment"
    MYSQL_HOST="manticore"
else
    echo "Running in local environment"
    MYSQL_HOST="0"
fi

# Function to validate MySQL response
validate_mysql_response() {
    local output="$1"
    local expected_count="$2"
    local expected_content="$3"
    
    # Check if there's an error in the response
    if echo "$output" | grep -q "ERROR"; then
        echo -e "${RED}❌ MySQL Error: $(echo "$output" | grep "ERROR")${NC}"
        return 1
    fi
    
    # Count the number of rows (each row starts with *************************** row)
    local row_count=$(echo "$output" | grep -c "row \*")
    
    # If expected_count is provided, verify the count
    if [ ! -z "$expected_count" ]; then
        if [ "$row_count" -ne "$expected_count" ]; then
            echo -e "${RED}❌ Expected $expected_count results, but got $row_count${NC}"
            return 1
        fi
    fi
    
    # If expected_content is provided, check if it appears in results
    if [ ! -z "$expected_content" ]; then
        if ! echo "$output" | grep -q "content: .*$expected_content"; then
            echo -e "${RED}❌ Expected content not found in results: $expected_content${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}✓ Valid response with $row_count results${NC}"
    
    # Show document details
    echo -e "${YELLOW}Documents found:${NC}"
    echo "$output" | awk '/\*\*\*/ {p=1;next} p&&/^$/{p=0} p' | sed 's/^/  /'
    
    return 0
}

run_test() {
    local description="$1"
    local query="$2"
    local expected_count="$3"
    local expected_content="$4"
    
    echo -e "\n----------------------------------------"
    echo "Testing search: $description"
    
    # Execute MySQL query and capture output
    output=$(docker-compose exec manticore mysql -h $MYSQL_HOST -P 9306 -e "SELECT id, title, content FROM documents_idx WHERE MATCH('$query')\G")
    
    # Print raw output for debugging
    echo -e "\nRaw MySQL output:"
    echo "$output"
    echo
    
    # Validate the response
    validate_mysql_response "$output" "$expected_count" "$expected_content"
}

echo "Starting Manticore direct search tests..."

# Check Manticore service status
echo -e "\n${BLUE}Checking Manticore service status...${NC}"
docker-compose exec manticore mysql -h $MYSQL_HOST -P 9306 -e "SHOW STATUS" || {
    echo -e "${RED}Failed to connect to Manticore Search${NC}"
    echo -e "${YELLOW}Checking Manticore container status...${NC}"
    docker-compose ps manticore
    echo -e "${YELLOW}Manticore container logs:${NC}"
    docker-compose logs manticore
    exit 1
}

# Check index status
echo -e "\n${BLUE}Checking index status...${NC}"
docker-compose exec manticore mysql -h $MYSQL_HOST -P 9306 -e "SHOW TABLES" || {
    echo -e "${RED}Failed to list tables${NC}"
    exit 1
}

# Check index structure
echo -e "\n${BLUE}Checking index structure...${NC}"
docker-compose exec manticore mysql -h $MYSQL_HOST -P 9306 -e "DESCRIBE documents_idx" || {
    echo -e "${RED}Failed to describe index${NC}"
    exit 1
}

# Check current data in index
echo -e "\n${BLUE}Checking current data in index...${NC}"
docker-compose exec manticore mysql -h $MYSQL_HOST -P 9306 -e "SELECT COUNT(*) FROM documents_idx" || {
    echo -e "${RED}Failed to count documents${NC}"
    exit 1
}

# Test Chinese character search
run_test "Chinese word '测试' (test)" "测试" 2 "测试文档"

# Test another Chinese character search
run_test "Chinese word '中文' (Chinese)" "中文" 3 "中文内容"

# Test English word search
run_test "English word 'test'" "test" 2 "test document"

# Test another English word search
run_test "English word 'english'" "english" 2 "English document"

# Test English phrase search
run_test "English phrase 'search functionality'" "search functionality" 1 "search functionality"

# Test all documents
echo -e "\n----------------------------------------"
echo "Showing all documents in the index:"
output=$(docker-compose exec manticore mysql -h $MYSQL_HOST -P 9306 -e "SELECT id, title, content FROM documents_idx\G")
echo "$output"
validate_mysql_response "$output" 5

echo -e "\n----------------------------------------"
echo "Manticore direct search tests completed." 