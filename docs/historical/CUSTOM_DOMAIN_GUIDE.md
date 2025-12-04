# 🌐 Custom Domain Setup Guide

## Why Use a Custom Domain?

| Feature | Railway Default (*.up.railway.app) | Custom Domain |
|---------|----------------------------------|---------------|
| **Professional** | ❌ Generic | ✅ Branded |
| **WhatsApp Webhook** | ⚠️ Works but less professional | ✅ Perfect for business |
| **SSL Certificate** | ✅ Automatic | ✅ Automatic (free) |
| **SEO** | ❌ Poor | ✅ Better |
| **Cost** | Free | **Free on Railway** |
| **Trust** | ⚠️ Users may be wary | ✅ Builds trust |

## 🚀 Quick Domain Setup (Railway)

### Step 1: Add Domain to Railway
1. Go to Railway Dashboard → Your Project
2. Click **"Settings"** tab
3. Click **"Domains"** section
4. Click **"Add Domain"**
5. Enter your domain (e.g., `api.autifyme.com` or `autifyme.com`)

### Step 2: Update DNS Records

Railway will show you exactly what DNS records to add. Here's what you'll typically need:

#### For Subdomain (api.autifyme.com):
```
Type: CNAME
Name: api
Value: your-app-name.up.railway.app
TTL: 300 (or default)
```

#### For Apex Domain (autifyme.com):
```
Type: CNAME
Name: @
Value: your-app-name.up.railway.app
TTL: 300 (or default)
```

**Note:** Some DNS providers call the "Name" field "Host" or "Subdomain".

### Step 3: Wait for DNS Propagation
- DNS changes take 5-30 minutes to propagate globally
- Railway will show a green checkmark when domain is verified
- SSL certificate is issued automatically (may take a few minutes)

### Step 4: Test Your Domain

Use the domain checker script:
```bash
python scripts/check-domain.py api.autifyme.com
```

Or manually test:
```bash
curl https://api.autifyme.com/health
# Should return: {"status": "healthy", "service": "autifyme-webhook"}
```

## 🛠️ Popular DNS Providers Setup

### Namecheap
1. Login to Namecheap → Domain List
2. Click "Manage" next to your domain
3. Go to "Advanced DNS" tab
4. Add the CNAME record as shown by Railway

### GoDaddy
1. Login to GoDaddy → My Products
2. Click domain → DNS
3. Click "Add" → CNAME record
4. Enter details as shown by Railway

### Cloudflare
1. Login to Cloudflare → Your Domain
2. Go to DNS tab
3. Click "Add record" → CNAME
4. Enter details as shown by Railway

### Hostinger
1. Login to Hostinger → Domains
2. Click domain → DNS / Nameservers
3. Add CNAME record as shown by Railway

## 🔍 Domain Troubleshooting

### Issue: "Domain not verified"
**Solution:**
- Wait 10-15 minutes for DNS propagation
- Check DNS records are exactly as Railway instructed
- Some providers hide the root domain (@) - make sure it's set correctly

### Issue: SSL Certificate Pending
**Solution:**
- SSL certificates are issued automatically by Railway
- May take up to 10 minutes after DNS verification
- Check Railway dashboard for certificate status

### Issue: Connection Refused
**Solution:**
- Verify Railway deployment is healthy (green status)
- Check domain points to correct Railway URL
- Test with: `curl https://your-app-name.up.railway.app/health`

### Issue: WhatsApp Webhook Errors
**Solution:**
- WhatsApp requires HTTPS - custom domain ensures this
- Update webhook URL in Meta Developer Console
- Test webhook verification: `GET /webhook?hub.verify_token=YOUR_TOKEN`

## 📋 Domain Best Practices

### 1. Choose the Right Domain Structure

**Option A: Subdomain (Recommended)**
- `api.autifyme.com` - Separate API from website
- `webhook.autifyme.com` - Clearly indicates webhook endpoint
- Easier to manage SSL certificates

**Option B: Apex Domain**
- `autifyme.com` - Uses main domain
- Better for marketing but mixes concerns

### 2. DNS Record Tips

- **TTL**: Use 300 seconds (5 minutes) for faster updates
- **CNAME vs A Record**: Railway requires CNAME records
- **Multiple Records**: Only add the one Railway specifies

### 3. SSL Certificate Management

- Railway handles SSL certificates automatically
- Free Let's Encrypt certificates included
- Auto-renews before expiration
- Covers both domain and www subdomain

### 4. Domain Monitoring

Regular checks:
```bash
# Health check
curl https://api.autifyme.com/health

# SSL certificate expiry (replace with your domain)
openssl s_client -connect api.autifyme.com:443 -servername api.autifyme.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

## 🚀 Production Domain Checklist

- [ ] Domain added to Railway dashboard
- [ ] DNS records configured correctly
- [ ] DNS propagation completed (green checkmark in Railway)
- [ ] SSL certificate issued (padlock icon in browser)
- [ ] Health endpoint responding: `/health`
- [ ] Webhook verification working: `/webhook`
- [ ] WhatsApp Business API webhook URL updated
- [ ] Test message sent successfully

## 💡 Pro Tips

1. **Domain Aliases**: Railway supports multiple domains pointing to same app
2. **www Subdomain**: Automatically included with SSL
3. **Domain Transfer**: Can move domain from another provider
4. **Monitoring**: Set up uptime monitoring for your domain
5. **CDN**: Consider Cloudflare in front for additional performance/caching

## 🆘 Need Help?

- **Railway Docs**: [railway.app/docs](https://docs.railway.app/docs/custom-domains)
- **DNS Checker**: [dnschecker.org](https://dnschecker.org) - verify propagation
- **SSL Checker**: [ssllabs.com/ssltest](https://www.ssllabs.com/ssltest) - check certificates

Your custom domain will make AutifyME look professional and work perfectly with WhatsApp webhooks! 🌟
