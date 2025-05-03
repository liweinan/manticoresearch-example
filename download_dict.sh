#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p data

# Check if proxy is set in environment variables
if [ -n "$http_proxy" ] && [ -n "$https_proxy" ]; then
    # Use environment proxy settings
    echo "Using proxy settings: $http_proxy"
    curl --proxy "$http_proxy" -o data/dict.txt.big https://raw.githubusercontent.com/fxsjy/jieba/master/extra_dict/dict.txt.big
else
    # Try direct download
    echo "Downloading without proxy"
    curl -o data/dict.txt.big https://raw.githubusercontent.com/fxsjy/jieba/master/extra_dict/dict.txt.big
fi

# Verify the download
if [ -f "data/dict.txt.big" ]; then
    echo "Dictionary downloaded successfully"
    ls -l data/dict.txt.big
else
    echo "Failed to download dictionary"
    exit 1
fi 