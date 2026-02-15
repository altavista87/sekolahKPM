# EduSync - Netlify Deployment Package

**Version**: 1.0.1 (Self-Contained)  
**Status**: ✅ Ready for deployment

Serverless deployment package for EduSync on Netlify's platform.

## 🎯 What's Included

- ✅ Telegram Bot webhook handler
- ✅ REST API endpoints  
- ✅ Scheduled reminder checks
- ✅ Health monitoring endpoint
- ✅ Static status page
- ✅ Security hardening
- ✅ **All source files included** (self-contained)

## 🚀 Quick Deploy (3 Steps)

```bash
# 1. Extract and enter the package
unzip edusync-netlify-v1.0.1.zip
cd edusync-netlify

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Deploy
./deploy.sh production
```

Or use **Git-based deploy**:
1. Push this folder to GitHub
2. Connect to Netlify
3. Set environment variables in Netlify dashboard

## 📖 Documentation

- [Deployment Guide](DEPLOY.md) - Complete deployment instructions
- [Architecture](../docs/ARCHITECTURE.md) - System architecture
- [API Docs](../docs/API.md) - API reference

## 🔧 Configuration

Copy `.env.example` to `.env` and configure:

```bash
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=postgresql://...
GEMINI_API_KEY=your_key
```

## 🌐 Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/health` | Health check |
| `/api/webhook/telegram` | Telegram webhook |
| `/api/v1/*` | REST API |
| `/` | Status page |

## 📊 Monitoring

Visit your deployed site's root URL for the status dashboard.

## 🔒 Security

- Webhook signature validation
- CORS configured
- Environment variables for secrets
- Security headers enabled

## 💰 Costs

Netlify free tier includes:
- 125,000 function invocations/month
- 100 hours runtime/month
- 300 GB bandwidth/month

## 📝 License

MIT License - see LICENSE file
