# VCC Authentication Service

Flask service for automated Extend and Privacy VCC authentication on Google Cloud. Handles login, OTP verification, and token extraction via browser automation.

## Features

- Multi-platform support (Extend/Privacy)
- Automated browser auth with Camoufox
- Firebase OTP integration & token caching
- Proxy rotation support
- CORS enabled

## Quick Setup

1. **Install**
bash
pip install flask flask-cors google-cloud-firestore camoufox

Configure


Add Firebase service.json credentials
Create proxies.txt (optional): host:port:user:pass


Deploy to Google Cloud

bashgcloud run deploy --source . --allow-unauthenticated
API Usage
POST /authtask
bashcurl -X POST https://your-url/authtask \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password",
    "type": "Privacy"
  }'
Response:
json{
  "access_token": "eyJhbGc..."
}
