# Deploy FNO Dashboard to Render (Free)

**Free tier: 750 hours/month = always-on service**

## 🚀 Quick Deploy (5 minutes)

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up (GitHub recommended)
3. Authorize Render

### Step 2: Push to GitHub
```bash
git init
git add .
git commit -m "FNO Intelligence Dashboard"
git remote add origin https://github.com/YOUR_USERNAME/fno-dashboard
git push -u origin main
```

### Step 3: Create Render Service

1. Click **"New +"** in Render dashboard
2. Select **"Web Service"**
3. Click **"Deploy from a Git repository"**
4. **Connect GitHub** if needed
5. Search for `fno-dashboard` repo and select it
6. Fill in these settings:

```
Name: fno-dashboard
Environment: Python 3
Region: Any (Oregon is good)
Branch: main
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

7. Click **"Create Web Service"**

### Step 4: Add Environment Variables

While the build is running:

1. Scroll down to **"Environment"** section
2. Click **"Add Environment Variable"**
3. Add these 4 variables:

```
ZERODHA_API_KEY = your_api_key
ZERODHA_API_SECRET = your_api_secret
ZERODHA_ACCESS_TOKEN = your_access_token
PORT = 10000
```

4. Click **"Save"**
5. Render auto-redeploys with these variables

### Step 5: Test Your API

Render gives you a URL like:
```
https://fno-dashboard.onrender.com
```

Test it:
```bash
curl https://fno-dashboard.onrender.com/health
```

You should see:
```json
{"status":"healthy","zerodha_ready":true}
```

### Step 6: Update Dashboard

Edit `fno-dashboard-index.html`:

Find:
```javascript
const BASE_URL = 'http://localhost:5000';
```

Change to:
```javascript
const BASE_URL = 'https://fno-dashboard.onrender.com';
```

Push change:
```bash
git add fno-dashboard-index.html
git commit -m "Update API URL for Render"
git push origin main
```

Render auto-redeploys.

---

## ⚙️ Render Settings Explained

| Setting | Value | Why |
|---------|-------|-----|
| **Build Command** | `pip install -r requirements.txt` | Installs Python packages |
| **Start Command** | `gunicorn app:app` | Runs Flask app on port 10000 |
| **PORT env var** | 10000 | Render requires this specific port |
| **Free tier** | 750 hours/month | Enough for 24/7 always-on |

---

## 📊 What Happens After Deploy

1. Render builds your app (takes ~2 min)
2. Your Flask API starts running
3. Background thread starts auto-refresh (every 5 min)
4. Dashboard connects to Render API
5. You see live NIFTY signals ✓

---

## 🔄 Auto-Redeploy on Push

Every time you push to GitHub:
```bash
git add .
git commit -m "Update something"
git push origin main
```

Render automatically:
1. Pulls latest code
2. Rebuilds
3. Redeploys
4. No downtime ✓

---

## ⚠️ Render Free Tier Limits

✅ **Included:**
- 750 hours/month (24/7 service)
- 2 concurrent services
- Auto-redeploy on GitHub push
- Custom domain support
- HTTPS/SSL included

❌ **Not included:**
- No disk storage (data lost on restart)
- Spins down after 15 min inactivity (doesn't apply to free tier - stays on)
- 400MB disk space
- 512 MB RAM

**For trading signals:** Perfectly fine. Data is live from Zerodha API anyway.

---

## 🆘 Troubleshooting

### "Build failed"
- Check Python syntax errors
- Verify requirements.txt is correct
- Check Render logs

### "Health check failing"
- Wait 2-3 minutes after deploy
- Check environment variables are set
- Verify PORT is 10000

### "Zerodha not ready"
- Check all 3 env vars are set
- Verify access token is valid
- Regenerate token if expired

### "No data showing in dashboard"
- Click "Refresh Data" button
- Check API logs in Render dashboard
- Verify dashboard has correct API URL

---

## 📱 Access from Phone

Your Render URL works everywhere:
```
https://your-app.onrender.com
```

- Open in mobile browser
- Add to home screen
- Works like an app ✓

---

## 🔐 Security

- ✅ Environment variables encrypted
- ✅ HTTPS automatic
- ✅ No API keys in code
- ✅ No API keys in logs

---

## 📈 If You Need More

Render's paid plans start at **$7/month** for guaranteed uptime.

But the **free tier is perfect for trading**.

---

## 🎯 Next Steps

1. Create Render account
2. Follow steps 1-6 above
3. You're live in 10 minutes
4. Start trading with live signals

**That's it!** Same system, now on Render instead of Railway.
