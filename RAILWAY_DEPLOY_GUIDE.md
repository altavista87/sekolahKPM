# Railway Deployment Guide - Full Setup

Complete guide to deploy EduSync API with PostgreSQL on Railway.

---

## 🚀 Quick Deploy (One-Click)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/placeholder)

Or manual deploy:

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Deploy
railway up
```

---

## 📋 Prerequisites

- Railway account (free tier works)
- GitHub repository connected to Railway
- Telegram Bot Token (from @BotFather)
- Gemini API Key (optional, for AI features)

---

## 🔧 Step-by-Step Deployment

### Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `altavista87/sekolahKPM`

### Step 2: Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Wait for database to provision (30 seconds)
4. Railway auto-sets `DATABASE_URL` environment variable

### Step 3: Add Redis (Optional but Recommended)

1. Click "New" → "Database" → "Add Redis"
2. Used for caching and session storage

### Step 4: Configure Environment Variables

Go to Project → Variables and add:

#### Required Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | `123456789:ABC...` | From @BotFather |
| `SECRET_KEY` | Generate with `openssl rand -hex 32` | For JWT signing |
| `ENVIRONMENT` | `production` | Production mode |

#### Optional Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `GEMINI_API_KEY` | `AIza...` | Google Gemini API |
| `REDIS_URL` | Auto-set by Railway | If using Redis |
| `FRONTEND_URL` | `https://sekolahkpm.netlify.app` | Your Netlify site |

### Step 5: Deploy

1. Railway auto-deploys on git push
2. Or click "Deploy" in Railway dashboard
3. Wait for build (2-3 minutes)
4. Check logs for "Database initialized" message

---

## 🔗 Connect Netlify Frontend to Railway API

### Update Frontend API URL

In your Netlify site's environment variables:

```bash
# Set this in Netlify dashboard
API_URL=https://your-app-name.up.railway.app
```

Or update frontend code to use the Railway domain:

```javascript
// In your frontend JavaScript
const API_URL = process.env.API_URL || 'https://your-app-name.up.railway.app';
```

### CORS Configuration

Already configured in `api/main.py` to allow:
- `https://sekolahkpm.netlify.app`
- `https://*.netlify.app`
- Local development servers

---

## 🤖 Configure Telegram Bot Webhook

After deployment, set the webhook:

```bash
# Replace with your actual values
BOT_TOKEN="your_bot_token"
RAILWAY_URL="https://your-app-name.up.railway.app"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${RAILWAY_URL}/webhook/telegram\"}"
```

Verify webhook is set:

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

---

## 🧪 Testing the Deployment

### Test Health Endpoint

```bash
curl https://your-app-name.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

### Test API Endpoints

```bash
# List homework
curl https://your-app-name.up.railway.app/api/v1/homework

# Get user
curl https://your-app-name.up.railway.app/api/v1/users/1
```

### Test from Frontend

1. Open your Netlify site
2. Open browser console (F12)
3. Try API calls - they should reach Railway backend

---

## 📊 Railway Dashboard Features

### Monitoring

- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, disk usage
- **Deploys**: Deployment history and rollbacks

### Scaling

Railway automatically scales:
- CPU: Up to limits of your plan
- Memory: Auto-scales as needed
- Database: PostgreSQL handles concurrent connections

### Custom Domain (Optional)

1. Go to Service Settings → Domains
2. Click "Generate Domain" for Railway subdomain
3. Or "Custom Domain" for your own domain

---

## 🔒 Security Checklist

- [ ] `SECRET_KEY` changed from default
- [ ] `ENVIRONMENT` set to `production`
- [ ] Database credentials auto-managed by Railway
- [ ] CORS restricted to known origins
- [ ] Rate limiting enabled (60 req/min default)

---

## 🐛 Troubleshooting

### Database Connection Failed

```bash
# Check DATABASE_URL is set
railway variables

# Test connection manually
railway connect postgres
```

### CORS Errors from Frontend

1. Check Railway logs for blocked origins
2. Add your domain to `ALLOWED_ORIGINS` in `api/main.py`
3. Redeploy

### Bot Webhook Not Working

1. Verify webhook URL: `curl /getWebhookInfo`
2. Check Railway logs for webhook requests
3. Ensure `TELEGRAM_BOT_TOKEN` is set correctly

### Build Failures

```bash
# Check build logs in Railway dashboard
# Common issues:
# - Missing requirements.txt
# - Python version mismatch
# - Import errors
```

---

## 💰 Cost Estimation

| Resource | Free Tier | Paid (Pro) |
|----------|-----------|------------|
| **Compute** | 500 hours/month | $5/month + usage |
| **PostgreSQL** | 500 MB storage | $5/month + storage |
| **Redis** | Not included | $5/month |
| **Bandwidth** | 100 GB/month | Unlimited |

**Free tier is sufficient for:**
- Development/testing
- Small user base (< 1000 users)
- Moderate traffic

---

## 🔄 Updates and Maintenance

### Redeploy After Code Changes

```bash
git add .
git commit -m "Update API"
git push origin main
# Railway auto-deploys
```

### Database Migrations

```bash
# Connect to Railway
railway connect

# Run migrations
python -m alembic upgrade head
```

### Backup Database

```bash
# Railway provides automatic backups
# For manual backup:
railway connect postgres
pg_dump $DATABASE_URL > backup.sql
```

---

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Railway PostgreSQL](https://docs.railway.app/databases/postgresql)
- [FastAPI on Railway](https://docs.railway.app/guides/fastapi)

---

## ✅ Deployment Checklist

- [ ] Railway project created
- [ ] PostgreSQL database added
- [ ] Environment variables configured
- [ ] Deploy successful (green checkmark)
- [ ] Health endpoint returns 200
- [ ] Database shows "connected"
- [ ] Telegram webhook configured
- [ ] Frontend CORS working
- [ ] API calls from frontend succeed

---

**Your API should now be live on Railway!** 🎉
