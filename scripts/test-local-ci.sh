#!/bin/bash

# Local GitHub Actions Testing Script using act
# This script allows you to run GitHub Actions workflows locally
# Requires act to be installed: https://github.com/nektos/act

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Local GitHub Actions Testing with act${NC}"
echo "================================================="

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}❌ act is not installed. Please install it first:${NC}"
    echo "   macOS: brew install act"
    echo "   Linux: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    echo "   Windows: choco install act-cli"
    echo "   Or see: https://github.com/nektos/act#installation"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Function to run workflow with act
run_workflow() {
    local workflow_name="$1"
    local workflow_file="$2"
    local additional_args="$3"

    echo -e "\n${BLUE}🔄 Running workflow: $workflow_name${NC}"
    echo "File: $workflow_file"
    echo "Args: $additional_args"
    echo "---------------------------------------------------"

    if act -W ".github/workflows/$workflow_file" $additional_args; then
        echo -e "${GREEN}✅ $workflow_name completed successfully${NC}"
    else
        echo -e "${RED}❌ $workflow_name failed${NC}"
        return 1
    fi
}

# Parse command line arguments
WORKFLOW=""
PYTHON_VERSION=""
TEST_CATEGORY=""
LIST_JOBS=false
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --workflow|-w)
            WORKFLOW="$2"
            shift 2
            ;;
        --python-version|-p)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        --test-category|-c)
            TEST_CATEGORY="$2"
            shift 2
            ;;
        --list-jobs|-l)
            LIST_JOBS=true
            shift
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -w, --workflow WORKFLOW     Run specific workflow (pythonpackage|comprehensive-tests|documentation|codeql)"
            echo "  -p, --python-version VERSION Set Python version (3.10|3.11|3.12)"
            echo "  -c, --test-category CATEGORY Set test category for comprehensive tests (api-core|api-repositories|api-formats|cli|integration)"
            echo "  -l, --list-jobs             List all jobs without running"
            echo "  -n, --dry-run               Show what would be executed without running"
            echo "  -v, --verbose               Enable verbose output"
            echo "  -h, --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run main Python package tests"
            echo "  $0 -w comprehensive-tests -c api-core   # Run core API tests"
            echo "  $0 -w pythonpackage -p 3.11         # Run with Python 3.11"
            echo "  $0 -l                                # List all available jobs"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set verbose flag for act
VERBOSE_FLAG=""
if [ "$VERBOSE" = true ]; then
    VERBOSE_FLAG="--verbose"
fi

# List jobs if requested
if [ "$LIST_JOBS" = true ]; then
    echo -e "${YELLOW}📋 Available workflows and jobs:${NC}"
    echo ""
    for workflow in .github/workflows/*.yml; do
        if [ -f "$workflow" ]; then
            echo -e "${BLUE}$(basename "$workflow"):${NC}"
            act -W "$workflow" --list $VERBOSE_FLAG
            echo ""
        fi
    done
    exit 0
fi

# Set default workflow if not specified
if [ -z "$WORKFLOW" ]; then
    WORKFLOW="pythonpackage"
fi

# Build act arguments
ACT_ARGS="$VERBOSE_FLAG"

if [ -n "$PYTHON_VERSION" ]; then
    ACT_ARGS="$ACT_ARGS --env PYTHON_VERSION=$PYTHON_VERSION --matrix python-version:$PYTHON_VERSION"
fi

if [ -n "$TEST_CATEGORY" ]; then
    ACT_ARGS="$ACT_ARGS --matrix test-category:$TEST_CATEGORY"
fi

# Add secrets file if it exists
if [ -f ".secrets" ]; then
    ACT_ARGS="$ACT_ARGS --secret-file .secrets"
elif [ -f ".env" ]; then
    ACT_ARGS="$ACT_ARGS --env-file .env"
fi

# Show what would be executed in dry-run mode
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 Dry run mode - showing what would be executed:${NC}"
    echo "Workflow: $WORKFLOW"
    echo "Act args: $ACT_ARGS"
    echo ""
    echo "Command that would be run:"
    echo "act -W .github/workflows/${WORKFLOW}.yml $ACT_ARGS"
    exit 0
fi

# Run the specified workflow
case $WORKFLOW in
    pythonpackage|python|main)
        run_workflow "Python Package Tests" "pythonpackage.yml" "$ACT_ARGS"
        ;;
    comprehensive-tests|comprehensive|tests)
        if [ -n "$TEST_CATEGORY" ]; then
            echo -e "${YELLOW}🎯 Running test category: $TEST_CATEGORY${NC}"
        fi
        run_workflow "Comprehensive Test Suite" "comprehensive-tests.yml" "$ACT_ARGS"
        ;;
    documentation|docs)
        run_workflow "Documentation Build" "documentation.yml" "$ACT_ARGS"
        ;;
    codeql|security)
        run_workflow "CodeQL Analysis" "codeql-analysis.yml" "$ACT_ARGS"
        ;;
    all)
        echo -e "${YELLOW}🔄 Running all workflows...${NC}"
        run_workflow "Python Package Tests" "pythonpackage.yml" "$ACT_ARGS"
        run_workflow "Comprehensive Test Suite" "comprehensive-tests.yml" "$ACT_ARGS"
        run_workflow "Documentation Build" "documentation.yml" "$ACT_ARGS"
        echo -e "${GREEN}✅ All workflows completed${NC}"
        ;;
    *)
        echo -e "${RED}❌ Unknown workflow: $WORKFLOW${NC}"
        echo "Available workflows: pythonpackage, comprehensive-tests, documentation, codeql, all"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Local CI testing completed successfully!${NC}"
echo ""
echo -e "${BLUE}💡 Tips:${NC}"
echo "  • Use --list-jobs to see all available jobs"
echo "  • Use --dry-run to see what would be executed"
echo "  • Create a .secrets file for any required API tokens"
echo "  • Check Docker logs if containers fail to start"
