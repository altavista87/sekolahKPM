# Git-Based Netlify Deployment (Required for Python Functions)

**IMPORTANT**: Netlify Python Functions require Git-based deployment. Manual ZIP upload won't work.

## 🚀 Method 1: GitHub + Netlify (Recommended)

### Step 1: Create GitHub Repository

```bash
# In the edusync-netlify folder
cd /Users/sir/edusync-netlify

# Initialize git
git init
git add .
git commit -m "Initial commit - EduSync v1.0.1"

# Create repo on GitHub (via web or gh CLI)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/edusync-netlify.git
git branch -M main
git push -u origin main
```

### Step 2: Connect to Netlify

1. Go to [app.netlify.com](https://app.netlify.com)
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **GitHub**
4. Select your `edusync-netlify` repository
5. Configure build:
   - **Branch to deploy**: `main`
   - **Base directory**: (leave empty)
   - **Build command**: `pip install -r requirements-netlify.txt`
   - **Publish directory**: `static`
6. Click **Deploy site**

### Step 3: Environment Variables

In Netlify Dashboard → Site settings → Environment variables:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_key
```

### Step 4: Deploy

Netlify will automatically build and deploy when you push to GitHub.

---

## 🚀 Method 2: Netlify CLI (Alternative)

### Install CLI
```bash
npm install -g netlify-cli
```

### Login & Link
```bash
cd /Users/sir/edusync-netlify
netlify login
netlify init
# Choose "Create & configure a new site"
```

### Deploy
```bash
netlify deploy --prod --build
```

---

## 🔧 Why ZIP Upload Doesn't Work

Netlify Python Functions require:
1. **Dependency installation** via `pip`
2. **Build process** to bundle functions
3. **Python runtime** setup

These only happen during Git-based or CLI deployments.

---

## ✅ Verification After Deploy

Check Netlify Dashboard → **Functions** tab:
- Should see: `telegram-webhook`, `health`, `api`, `check-reminders`

Test endpoints:
```bash
# Health check
curl https://your-site.netlify.app/api/health

# Should return:
{"status":"healthy","services":{...}}
```

---

## 🐛 If Functions Still Don't Appear

### Check Build Log
In Netlify Dashboard → Deploys → Click latest deploy:
- Look for "Installing dependencies"
- Look for "Functions bundling"

### Common Issues

**"Python not found"**
- Add to `netlify.toml`:
```toml
[build.environment]
  PYTHON_VERSION = "3.11"
```

**"Module not found"**
- Add missing package to `requirements-netlify.txt`
- Re-deploy

**Functions too large**
- Reduce dependencies
- Use `requests` instead of `httpx` (smaller)
- Remove unused AI libraries

---

## 📦 Quick Start Script

Save as `setup-and-deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 EduSync Netlify Deployment"
echo ""

# Check prerequisites
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Install git first."
    exit 1
fi

if ! command -v netlify &> /dev/null; then
    echo "Installing Netlify CLI..."
    npm install -g netlify-cli
fi

# Git setup
if [ ! -d .git ]; then
    echo "📦 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit"
fi

# Netlify setup
echo "🔗 Connecting to Netlify..."
netlify login
netlify init

# Environment check
if [ ! -f .env ]; then
    echo "⚠️  Create .env file with your secrets:"
    echo "   TELEGRAM_BOT_TOKEN=..."
    echo "   DATABASE_URL=..."
    echo "   SECRET_KEY=..."
    exit 1
fi

# Deploy
echo "🚀 Deploying..."
netlify deploy --prod --build

echo ""
echo "✅ Done! Check your site URL above."
echo "📖 Next: Set environment variables in Netlify dashboard"
```

Make executable: `chmod +x setup-and-deploy.sh`

---

## 🎯 Success Criteria

After deployment, you should see:

✅ **Deploy log shows**: "4 functions bundled"  
✅ **Functions tab** lists all 4 functions  
✅ **Site URL** shows status page  
✅ **API endpoints** respond correctly  

---

**Need help?** Check the full guide in `DEPLOY.md`
