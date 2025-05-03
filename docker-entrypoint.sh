#!/bin/bash

# Generate config from the shell script
bash /etc/manticoresearch/manticore.conf.sh > /etc/manticoresearch/manticore.conf.generated

# Copy the generated config to the final location
cp /etc/manticoresearch/manticore.conf.generated /etc/manticoresearch/manticore.conf

# Ensure data directory exists and has correct permissions
mkdir -p /var/lib/manticore
chown -R manticore:manticore /var/lib/manticore
chmod -R 755 /var/lib/manticore

# Wait for PostgreSQL to be ready and the documents table to exist
echo "Waiting for PostgreSQL and documents table to be ready..."
MAX_RETRIES=60  # 5 minutes with 5-second intervals
retry_count=0

while [ $retry_count -lt $MAX_RETRIES ]; do
    # Check if PostgreSQL is ready
    if PGPASSWORD=postgres psql -h postgres -U postgres -d search_db -c '\q' 2>/dev/null; then
        # Check if documents table exists and has data
        if PGPASSWORD=postgres psql -h postgres -U postgres -d search_db -c "SELECT COUNT(*) FROM documents;" 2>/dev/null | grep -q '[1-9]'; then
            echo "PostgreSQL and documents table are ready!"
            break
        else
            echo "PostgreSQL is ready but documents table is not ready yet..."
            # Check if the app is running
            if curl -s http://app:5000/ > /dev/null; then
                echo "Flask app is running, waiting for database initialization..."
            else
                echo "Flask app is not running yet..."
            fi
        fi
    else
        echo "PostgreSQL is not ready yet..."
    fi
    
    retry_count=$((retry_count + 1))
    if [ $retry_count -eq $MAX_RETRIES ]; then
        echo "Timeout waiting for PostgreSQL and documents table to be ready. Exiting..."
        exit 1
    fi
    
    echo "Waiting for PostgreSQL and documents table... (attempt $retry_count/$MAX_RETRIES)"
    sleep 5
done

# Create initial index as manticore user
su -s /bin/bash manticore -c "indexer --all --config /etc/manticoresearch/manticore.conf"

# Start searchd in non-daemon mode
exec searchd --config /etc/manticoresearch/manticore.conf --nodetach 