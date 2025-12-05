#!/bin/bash
#
# Remove consumption tracking cron jobs
# Run this script to uninstall all periodic jobs
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Remove Consumption Tracking Cron Jobs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if there are any consumption tracking jobs
if ! crontab -l 2>/dev/null | grep -q "consumption_periodic_jobs.py\|reconcile_consumption.py"; then
    echo -e "${YELLOW}No consumption tracking cron jobs found${NC}"
    exit 0
fi

# Show current jobs that will be removed
echo -e "${YELLOW}Jobs to be removed:${NC}"
echo -e "${GREEN}───────────────────────────────────────${NC}"
crontab -l 2>/dev/null | grep "consumption_periodic_jobs.py\|reconcile_consumption.py"
echo -e "${GREEN}───────────────────────────────────────${NC}"
echo ""

# Ask for confirmation
read -p "Remove these cron jobs? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Removal cancelled${NC}"
    exit 0
fi

# Create temporary cron file without consumption jobs
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null | grep -v "consumption_periodic_jobs.py\|reconcile_consumption.py\|Consumption Tracking Maintenance" > "$TEMP_CRON" || true

# Install the cleaned crontab
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo ""
echo -e "${GREEN}✓${NC} Consumption tracking cron jobs removed successfully!"
echo ""

# Show remaining jobs (if any)
if crontab -l 2>/dev/null | grep -q "^[^#]"; then
    echo -e "${BLUE}Remaining cron jobs:${NC}"
    echo -e "${GREEN}───────────────────────────────────────${NC}"
    crontab -l
    echo -e "${GREEN}───────────────────────────────────────${NC}"
else
    echo -e "${YELLOW}No cron jobs remaining${NC}"
fi
echo ""
