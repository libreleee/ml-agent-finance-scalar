#!/usr/bin/env bash
# Prerequisite checker for ml-agent-finance-scalar
# Verifies that required tools are installed with appropriate versions

set -euo pipefail

echo "======================================"
echo "Checking Prerequisites"
echo "======================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

all_checks_passed=true

# Function to check command existence
check_command() {
    local cmd=$1
    local name=$2
    
    echo -n "Checking ${name}... "
    
    if ! command -v "${cmd}" &> /dev/null; then
        echo -e "${RED}NOT FOUND${NC}"
        echo "  ${name} is not installed or not in PATH"
        all_checks_passed=false
        return 1
    fi
    
    echo -e "${GREEN}FOUND${NC}"
    return 0
}

# Check Docker
echo "1. Docker Engine"
if check_command "docker" "Docker"; then
    docker_version=$(docker --version)
    echo "  Version: ${docker_version}"
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        echo -e "  Status: ${GREEN}Docker daemon is running${NC}"
    else
        echo -e "  Status: ${RED}Docker daemon is NOT running${NC}"
        echo "  Please start Docker Desktop or Docker Engine"
        all_checks_passed=false
    fi
else
    echo "  Install from: https://docs.docker.com/get-docker/"
fi
echo ""

# Check Docker Compose
echo "2. Docker Compose"
if check_command "docker" "Docker"; then
    # Check for docker compose (v2, built into docker)
    if docker compose version &> /dev/null; then
        compose_version=$(docker compose version)
        echo -e "  ${GREEN}FOUND${NC}"
        echo "  Version: ${compose_version}"
    # Check for docker-compose (v1, standalone)
    elif command -v docker-compose &> /dev/null; then
        compose_version=$(docker-compose --version)
        echo -e "  ${GREEN}FOUND${NC}"
        echo "  Version: ${compose_version}"
        echo -e "  ${YELLOW}Note: Using legacy docker-compose. Consider upgrading to 'docker compose'${NC}"
    else
        echo -e "  ${RED}NOT FOUND${NC}"
        echo "  Docker Compose is required"
        echo "  Install from: https://docs.docker.com/compose/install/"
        all_checks_passed=false
    fi
else
    echo -e "  ${RED}SKIPPED${NC} (Docker not found)"
fi
echo ""

# Check Python
echo "3. Python"
if check_command "python3" "Python"; then
    python_version=$(python3 --version)
    echo "  Version: ${python_version}"
    
    # Extract major.minor version - simpler approach for better compatibility
    py_version_info=$(python3 -c 'import sys; print(sys.version_info.major, sys.version_info.minor)')
    py_major=$(echo "$py_version_info" | cut -d' ' -f1)
    py_minor=$(echo "$py_version_info" | cut -d' ' -f2)
    py_version_num="${py_major}.${py_minor}"
    
    # Validate version numbers are numeric
    if [[ "$py_major" =~ ^[0-9]+$ ]] && [[ "$py_minor" =~ ^[0-9]+$ ]]; then
        # python3 command guarantees major version is 3, so we only check minor version
        if (( py_minor >= 11 )); then
            echo -e "  ${GREEN}Version check: OK (3.11+ required)${NC}"
        else
            echo -e "  ${YELLOW}Warning: Python 3.11+ recommended (found ${py_version_num})${NC}"
        fi
    else
        echo -e "  ${YELLOW}Warning: Could not verify Python version${NC}"
    fi
else
    echo "  Install from: https://www.python.org/downloads/"
fi
echo ""

# Check Java (for Spark)
echo "4. Java (for Spark)"
if check_command "java" "Java"; then
    java_version=$(java -version 2>&1 | head -n 1)
    echo "  Version: ${java_version}"
    
    # Check if Java 17+ is available
    # Extract version: handles both old format (1.8.0) and new format (17.0.1)
    # Use sed for better portability (works on macOS and Linux)
    java_version_string=$(java -version 2>&1 | head -n 1 | sed -n 's/.*version "\([^"]*\)".*/\1/p')
    
    # Check if version extraction was successful
    if [[ -n "$java_version_string" ]]; then
        # Extract major version number
        if [[ "$java_version_string" =~ ^1\. ]]; then
            # Old format: 1.8.0_292 -> extract 8
            java_major=$(echo "$java_version_string" | cut -d. -f2)
        else
            # New format: 17.0.1 -> extract 17
            java_major=$(echo "$java_version_string" | cut -d. -f1)
        fi
        
        # Validate that we have a numeric major version, then compare once
        if [[ "${java_major}" =~ ^[0-9]+$ ]]; then
            if (( java_major >= 17 )); then
                echo -e "  ${GREEN}Version check: OK (Java 17+ required for Spark)${NC}"
            else
                echo -e "  ${YELLOW}Warning: Java 17+ recommended for Spark (found Java ${java_major})${NC}"
            fi
        else
            echo -e "  ${YELLOW}Warning: Could not parse Java version${NC}"
        fi
    else
        echo -e "  ${YELLOW}Warning: Could not extract Java version${NC}"
    fi
else
    echo "  Required for Apache Spark"
    echo "  Install from: https://adoptium.net/"
fi
echo ""

# Summary
echo "======================================"
if [ "$all_checks_passed" = true ]; then
    echo -e "${GREEN}All required checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start services: docker compose up -d"
    echo "  2. Check services: docker compose ps"
    echo "  3. Follow docs/10_offline_mainline_A_build_run.md"
    exit 0
else
    echo -e "${RED}Some checks failed!${NC}"
    echo "Please install missing prerequisites before proceeding."
    exit 1
fi
