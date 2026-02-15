#!/bin/bash
# EduSync Netlify Deployment Script
# Usage: ./deploy.sh [staging|production]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      EduSync Netlify Deployer           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "netlify.toml" ]; then
    echo -e "${RED}Error: Must run from edusync-netlify directory${NC}"
    exit 1
fi

# Check for netlify CLI
if ! command -v netlify &> /dev/null; then
    echo -e "${YELLOW}Netlify CLI not found. Installing...${NC}"
    npm install -g netlify-cli
fi

# Check if logged in
echo -e "${BLUE}Checking Netlify authentication...${NC}"
if ! netlify status &> /dev/null; then
    echo -e "${YELLOW}Please login to Netlify:${NC}"
    netlify login
fi

# Get deployment target
TARGET=${1:-staging}
if [ "$TARGET" = "production" ] || [ "$TARGET" = "prod" ]; then
    DEPLOY_FLAGS="--prod"
    echo -e "${GREEN}Deploying to PRODUCTION${NC}"
else
    DEPLOY_FLAGS=""
    echo -e "${YELLOW}Deploying to STAGING (preview)${NC}"
    echo "Add 'production' argument to deploy to production"
fi

# Step 1: Copy source files
echo ""
echo -e "${BLUE}Step 1/5: Copying source files...${NC}"
if [ -d "../edusync-evaluation" ]; then
    python build.py
    echo -e "${GREEN}✓ Source files copied${NC}"
else
    echo -e "${YELLOW}⚠ Source directory not found. Assuming already copied.${NC}"
fi

# Step 2: Verify environment
echo ""
echo -e "${BLUE}Step 2/5: Verifying environment...${NC}"
REQUIRED_VARS=("TELEGRAM_BOT_TOKEN" "DATABASE_URL" "SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${YELLOW}⚠ Missing environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these in Netlify dashboard or .env file"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Environment variables OK${NC}"
fi

# Step 3: Install dependencies
echo ""
echo -e "${BLUE}Step 3/5: Installing dependencies...${NC}"
pip install -q -r requirements-netlify.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 4: Run tests
echo ""
echo -e "${BLUE}Step 4/5: Running tests...${NC}"
# Add your test commands here
# pytest tests/ -v
# For now, just check syntax
echo "Checking Python syntax..."
python -m py_compile netlify/functions/*.py
echo -e "${GREEN}✓ Syntax check passed${NC}"

# Step 5: Deploy
echo ""
echo -e "${BLUE}Step 5/5: Deploying to Netlify...${NC}"
DEPLOY_OUTPUT=$(netlify deploy $DEPLOY_FLAGS --build --json 2>&1) || {
    echo -e "${RED}✗ Deployment failed${NC}"
    echo "$DEPLOY_OUTPUT"
    exit 1
}

# Extract URL from output
DEPLOY_URL=$(echo "$DEPLOY_OUTPUT" | grep -o '"deploy_url":"[^"]*"' | cut -d'"' -f4)
SITE_URL=$(echo "$DEPLOY_OUTPUT" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Deployment Successful! 🚀           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Preview URL:${NC} $DEPLOY_URL"
echo -e "${BLUE}Site URL:${NC} $SITE_URL"
echo ""

# Next steps
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Visit your site: $SITE_URL"
echo "2. Check health endpoint: $SITE_URL/api/health"
echo "3. Set Telegram webhook (if not done):"
echo ""
echo "   curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \\"
echo "     -d url=$SITE_URL/api/webhook/telegram"
echo ""

if [ -z "$DEPLOY_FLAGS" ]; then
    echo -e "${YELLOW}To deploy to production, run:${NC}"
    echo "  ./deploy.sh production"
fi

echo -e "${GREEN}Done!${NC}"
