# Railway Deployment Troubleshooting

## Current Issue: DATABASE_URL Not Set

The logs show `DATABASE_URL not set, using SQLite fallback`. This means you haven't added a PostgreSQL database to your Railway project yet.

---

## 🔧 Fix Steps

### Step 1: Add PostgreSQL Database

1. Go to [railway.app/dashboard](https://railway.app/dashboard)
2. Click your **EduSync project**
3. Click **"New"** button
4. Select **"Database"** → **"Add PostgreSQL"**
5. Wait 30 seconds for it to provision
6. Railway will **auto-set** `DATABASE_URL` environment variable

### Step 2: Redeploy

After adding PostgreSQL:
1. Go to your **service** (not the database)
2. Click **"Deploy"** button
3. Wait for new deployment

---

## ✅ Verify Fix

Check the new deployment logs for:
```
✅ Database: connected
```

If you see this, the healthcheck should pass!

---

## 🧪 Test Your API

Once deployed:

```bash
# Replace with your Railway URL
curl https://your-app.up.railway.app/health
```

Expected:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

---

## 🐛 If Still Failing

### Check These in Railway Dashboard:

1. **Variables tab** - Should show `DATABASE_URL` auto-populated
2. **Deploy logs** - Look for "Database initialized" message
3. **Metrics tab** - Check if service is crashing/restarting

### Common Issues:

| Issue | Solution |
|-------|----------|
| `DATABASE_URL` missing | Add PostgreSQL database (Step 1 above) |
| Healthcheck timeout | Service still starting, wait 60 seconds |
| Import errors | Check deploy logs for missing packages |

---

## 📋 Quick Checklist

- [ ] PostgreSQL database added to project
- [ ] `DATABASE_URL` visible in Variables tab
- [ ] Service redeployed after adding database
- [ ] Health endpoint returns 200

---

## 💡 Alternative: Use SQLite (Temporary)

If you just want to test the deployment without PostgreSQL:

The app will automatically use SQLite as fallback. It will work for testing, but data won't persist between restarts.

To use this temporarily, just redeploy without adding PostgreSQL.

---

## 🆘 Still Stuck?

Try the **minimal test** to isolate the issue:

1. Create a new file `test_minimal.py`:
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
```

2. Update `railway.toml`:
```toml
[deploy]
startCommand = "uvicorn test_minimal:app --host 0.0.0.0 --port $PORT"
```

3. Push and see if this basic app deploys

If this works, the issue is with the database/config. If not, it's a Railway setup issue.

---

**Next step: Add PostgreSQL database and redeploy!**
