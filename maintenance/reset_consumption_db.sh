#!/bin/bash
# Script to reset the consumption database and force bootstrap with new schema

echo "=========================================="
echo "Resetting Consumption Database"
echo "=========================================="
echo ""

DB_PATH="src/trusted_data_agent/auth/tda_auth.db"

if [ -f "$DB_PATH" ]; then
    echo "✅ Found database at: $DB_PATH"
    echo "📦 Backing up current database..."
    cp "$DB_PATH" "${DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup created"
    echo ""
    echo "🗑️  Deleting current database to force fresh schema..."
    rm "$DB_PATH"
    echo "✅ Database deleted"
else
    echo "ℹ️  No existing database found at: $DB_PATH"
fi

echo ""
echo "=========================================="
echo "✅ Ready for Bootstrap"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the application"
echo "2. The database will be recreated with new schema"
echo "3. consumption_turns table will have user_query and session_name columns"
echo "4. Ask a few questions to populate data"
echo "5. Refresh the Execution Insights dashboard"
echo ""
