# EduSync Netlify Deployment Guide

This package contains everything needed to deploy EduSync to Netlify's serverless platform.

## 📋 Prerequisites

- Netlify account
- Telegram Bot Token (from @BotFather)
- Database (Neon PostgreSQL, Supabase, or similar)
- (Optional) Redis instance (Upstash)

## 🚀 Quick Deploy

### 1. Fork/Clone Repository

```bash
git clone <your-repo-url>
cd edusync-netlify
```

### 2. Connect to Netlify

**Option A: Netlify CLI**
```bash
npm install -g netlify-cli
netlify login
netlify init
```

**Option B: Netlify UI**
1. Go to [netlify.com](https://netlify.com)
2. Click "Add new site" → "Import an existing project"
3. Connect your Git provider
4. Select the `edusync-netlify` directory

### 3. Configure Environment Variables

In Netlify Dashboard → Site Settings → Environment Variables:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
SECRET_KEY=your_random_secret_key

# Optional AI Services
GEMINI_API_KEY=your_gemini_key
TOGETHER_API_KEY=your_together_key
OPENAI_API_KEY=your_openai_key

# Optional Redis
REDIS_URL=redis://default:pass@host:6379

# Webhook Security
TELEGRAM_WEBHOOK_SECRET=random_secret_string
WEBHOOK_URL=https://your-site.netlify.app/api/webhook/telegram

# Feature Flags
ENABLE_AI_ENHANCEMENT=true
ENABLE_WHATSAPP=false
```

### 4. Deploy

```bash
netlify deploy --prod
```

Or push to your repository for automatic deployment.

---

## 📁 Package Structure

```
edusync-netlify/
├── netlify.toml              # Netlify configuration
├── requirements-netlify.txt  # Python dependencies
├── build.py                  # Build script
├── DEPLOY.md                 # This file
│
├── netlify/
│   └── functions/
│       ├── telegram-webhook.py    # Telegram bot webhook
│       ├── whatsapp-webhook.py    # WhatsApp webhook (optional)
│       ├── api.py                 # REST API endpoints
│       ├── health.py              # Health check
│       └── check-reminders.py     # Scheduled reminders
│
├── static/
│   └── index.html            # Status page
│
└── [source files copied during build]
    ├── bot/
    ├── api/
    ├── database/
    └── ...
```

---

## 🔧 Configuration Details

### `netlify.toml`

Key settings:
- **Functions directory**: `netlify/functions`
- **Publish directory**: `static` (for status page)
- **Redirects**: Route API calls to functions
- **Scheduled functions**: Reminder checks

### Scheduled Functions

Netlify runs scheduled functions automatically:
- `check-reminders`: Runs daily at 8 AM, 1 PM, 6 PM

### Database Setup

**Option 1: Neon PostgreSQL (Recommended)**
1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project
3. Copy the connection string to `DATABASE_URL`

**Option 2: Supabase**
1. Create project at [supabase.com](https://supabase.com)
2. Use connection pooling for serverless

**Run Migrations:**
```bash
# Local
alembic upgrade head

# Or use Netlify's deploy hooks to run migrations
```

---

## 🧪 Testing

### 1. Health Check

```bash
curl https://your-site.netlify.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T10:30:00",
  "services": {
    "telegram": "configured",
    "database": "configured",
    "ai": ["gemini", "together"]
  }
}
```

### 2. Telegram Webhook

Set webhook URL:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-site.netlify.app/api/webhook/telegram",
    "secret_token": "your_webhook_secret"
  }'
```

### 3. Test Bot

1. Open Telegram
2. Find your bot
3. Send `/start`
4. Try sending a homework photo

---

## 🔒 Security Considerations

### Environment Variables

- Never commit `.env` files
- Use Netlify's environment variables UI
- Rotate secrets regularly

### Webhook Security

The webhook endpoints validate:
1. `X-Telegram-Bot-Api-Secret-Token` header (Telegram)
2. `X-Hub-Signature-256` header (WhatsApp)

### CORS

Configured in `netlify.toml`:
- Allowed origins: `https://edusync.app`, `https://*.edusync.app`
- Credentials enabled for authenticated requests

---

## 📊 Monitoring

### Netlify Analytics

Enable in Dashboard → Analytics:
- Function invocations
- Error rates
- Performance metrics

### Logs

View function logs:
```bash
netlify logs:function
```

Or in Dashboard → Functions → Logs

### Alerts

Set up notifications for:
- Failed function invocations
- High error rates
- Scheduled function failures

---

## 🐛 Troubleshooting

### Function Timeout

If functions timeout:
1. Check cold start times
2. Optimize database queries
3. Use connection pooling
4. Consider upgrading to Netlify Pro for longer timeouts

### Size Limits

If deployment fails due to size:
1. Remove unused dependencies
2. Use `minify_for_serverless()` in build.py
3. Enable Netlify Large Functions addon

### Database Connection Issues

For serverless cold starts:
1. Use connection pooling (PgBouncer)
2. Enable `pool_pre_ping` in SQLAlchemy
3. Consider using a serverless database (Neon, Supabase)

### Import Errors

If functions fail with import errors:
1. Check `requirements-netlify.txt`
2. Ensure `__init__.py` files exist
3. Verify PYTHONPATH in `netlify.toml`

---

## 💰 Cost Optimization

### Free Tier Limits

Netlify free tier includes:
- 125,000 function invocations/month
- 100 hours function runtime/month
- 300 GB bandwidth/month

### Cost Reduction Tips

1. **Cache responses** where possible
2. **Optimize database queries** to reduce execution time
3. **Use scheduled functions** efficiently (not too frequent)
4. **Monitor function duration** and optimize slow ones

### When to Upgrade

Consider Netlify Pro ($19/month) for:
- More function invocations
- Longer timeout (26s vs 10s)
- Larger function size (50MB vs 10MB)
- Priority support

---

## 🔄 CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Netlify

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Netlify
        uses: netlify/actions/cli@master
        with:
          args: deploy --prod --dir=.
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

---

## 📚 Additional Resources

- [Netlify Functions Docs](https://docs.netlify.com/functions/overview/)
- [Netlify Scheduled Functions](https://docs.netlify.com/functions/scheduled-functions/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI on Netlify](https://www.fastapi-on-netlify.com/)

---

## 🆘 Support

If you encounter issues:

1. Check Netlify Function logs
2. Verify environment variables
3. Test webhook endpoint manually
4. Review this deployment guide
5. Open an issue on GitHub

---

**Happy Deploying! 🚀**
