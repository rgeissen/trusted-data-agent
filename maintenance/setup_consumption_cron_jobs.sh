#!/bin/bash
#
# Setup cron jobs for consumption tracking maintenance
# Run this script once to install all periodic jobs
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the absolute path to the uderia directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UDERIA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONDA_ENV="tda"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Consumption Tracking Cron Job Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Uderia Directory: ${GREEN}$UDERIA_DIR${NC}"
echo -e "Conda Environment: ${GREEN}$CONDA_ENV${NC}"
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}ERROR: conda command not found${NC}"
    echo "Please ensure conda is installed and in your PATH"
    exit 1
fi

# Verify the conda environment exists
if ! conda env list | grep -q "^$CONDA_ENV "; then
    echo -e "${RED}ERROR: Conda environment '$CONDA_ENV' not found${NC}"
    echo "Please create the environment first or update CONDA_ENV in this script"
    exit 1
fi

echo -e "${GREEN}✓${NC} Conda environment '$CONDA_ENV' found"
echo ""

# Create temporary cron file
TEMP_CRON=$(mktemp)

# Get current crontab (if any) and filter out old consumption jobs
crontab -l 2>/dev/null | grep -v "consumption_periodic_jobs.py\|reconcile_consumption.py" > "$TEMP_CRON" || true

echo -e "${YELLOW}Adding new cron jobs...${NC}"
echo ""

# Add new cron jobs with comments
cat >> "$TEMP_CRON" << EOF

# =============================================================================
# Consumption Tracking Maintenance Jobs (Auto-generated)
# =============================================================================

# Hourly: Reset rate limit counters
0 * * * * cd $UDERIA_DIR && conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job hourly >> logs/cron_hourly.log 2>&1

# Daily: Update 24h velocity metrics
0 0 * * * cd $UDERIA_DIR && conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job daily >> logs/cron_daily.log 2>&1

# Monthly: Rollover periods and archive data (1st of each month)
0 0 1 * * cd $UDERIA_DIR && conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job monthly >> logs/cron_monthly.log 2>&1

# Weekly: Reconcile consumption data (Sundays at 2 AM)
0 2 * * 0 cd $UDERIA_DIR && conda run -n $CONDA_ENV python maintenance/reconcile_consumption.py --fix >> logs/cron_reconcile.log 2>&1

EOF

# Display the cron jobs that will be added
echo -e "${BLUE}Cron jobs to be installed:${NC}"
echo -e "${GREEN}───────────────────────────────────────${NC}"
tail -9 "$TEMP_CRON"
echo -e "${GREEN}───────────────────────────────────────${NC}"
echo ""

# Ask for confirmation
read -p "Install these cron jobs? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installation cancelled${NC}"
    rm "$TEMP_CRON"
    exit 0
fi

# Install the crontab
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo ""
echo -e "${GREEN}✓${NC} Cron jobs installed successfully!"
echo ""

# Verify installation
echo -e "${BLUE}Current crontab:${NC}"
echo -e "${GREEN}───────────────────────────────────────${NC}"
crontab -l | grep -A 10 "Consumption Tracking"
echo -e "${GREEN}───────────────────────────────────────${NC}"
echo ""

# Create log directory if it doesn't exist
mkdir -p "$UDERIA_DIR/logs"
echo -e "${GREEN}✓${NC} Log directory created/verified: $UDERIA_DIR/logs"
echo ""

# Show schedule summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Job Schedule Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Hourly${NC}   - Every hour at :00 - Rate limit reset"
echo -e "${GREEN}Daily${NC}    - Every day at midnight - Velocity update"
echo -e "${GREEN}Monthly${NC}  - 1st of each month at midnight - Period rollover"
echo -e "${GREEN}Weekly${NC}   - Sundays at 2 AM - Data reconciliation"
echo ""

# Show log file locations
echo -e "${BLUE}Log Files:${NC}"
echo -e "  Hourly:      $UDERIA_DIR/logs/cron_hourly.log"
echo -e "  Daily:       $UDERIA_DIR/logs/cron_daily.log"
echo -e "  Monthly:     $UDERIA_DIR/logs/cron_monthly.log"
echo -e "  Reconcile:   $UDERIA_DIR/logs/cron_reconcile.log"
echo ""

# Show helpful commands
echo -e "${BLUE}Helpful Commands:${NC}"
echo -e "  View crontab:           ${YELLOW}crontab -l${NC}"
echo -e "  Edit crontab:           ${YELLOW}crontab -e${NC}"
echo -e "  Remove all jobs:        ${YELLOW}crontab -r${NC}"
echo -e "  View hourly log:        ${YELLOW}tail -f $UDERIA_DIR/logs/cron_hourly.log${NC}"
echo -e "  Test hourly job:        ${YELLOW}cd $UDERIA_DIR && conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job hourly${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
