#!/bin/bash
#
# Test consumption tracking cron jobs manually
# Run individual jobs to verify they work correctly
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
echo -e "${BLUE}Test Consumption Tracking Jobs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}ERROR: conda command not found${NC}"
    exit 1
fi

# Function to run a job and report results
run_job() {
    local job_name=$1
    local job_command=$2
    
    echo -e "${BLUE}Testing: ${job_name}${NC}"
    echo -e "${YELLOW}Command: ${job_command}${NC}"
    echo -e "${GREEN}───────────────────────────────────────${NC}"
    
    cd "$UDERIA_DIR"
    
    if eval "$job_command"; then
        echo -e "${GREEN}───────────────────────────────────────${NC}"
        echo -e "${GREEN}✓ ${job_name} completed successfully${NC}"
    else
        echo -e "${GREEN}───────────────────────────────────────${NC}"
        echo -e "${RED}✗ ${job_name} failed${NC}"
        return 1
    fi
    
    echo ""
}

# Menu for selecting which job to test
echo "Select job to test:"
echo ""
echo "  1) Hourly - Rate limit reset"
echo "  2) Daily - Velocity update"
echo "  3) Monthly - Period rollover"
echo "  4) Weekly - Data reconciliation"
echo "  5) All jobs (sequential)"
echo "  0) Exit"
echo ""
read -p "Enter choice [0-5]: " choice

case $choice in
    1)
        run_job "Hourly Rate Limit Reset" \
            "conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job hourly"
        ;;
    2)
        run_job "Daily Velocity Update" \
            "conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job daily"
        ;;
    3)
        run_job "Monthly Period Rollover" \
            "conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job monthly"
        ;;
    4)
        run_job "Weekly Data Reconciliation" \
            "conda run -n $CONDA_ENV python maintenance/reconcile_consumption.py --fix"
        ;;
    5)
        echo -e "${BLUE}Running all jobs sequentially...${NC}"
        echo ""
        
        run_job "1. Hourly Rate Limit Reset" \
            "conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job hourly"
        
        run_job "2. Daily Velocity Update" \
            "conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job daily"
        
        run_job "3. Monthly Period Rollover" \
            "conda run -n $CONDA_ENV python maintenance/consumption_periodic_jobs.py --job monthly"
        
        run_job "4. Weekly Data Reconciliation" \
            "conda run -n $CONDA_ENV python maintenance/reconcile_consumption.py --fix"
        
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}All jobs completed!${NC}"
        echo -e "${GREEN}========================================${NC}"
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}Test Complete${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  - Check the output above for any errors"
echo -e "  - Verify database changes in tda_auth.db"
echo -e "  - If tests pass, install cron jobs with:"
echo -e "    ${GREEN}./maintenance/setup_consumption_cron_jobs.sh${NC}"
echo ""
