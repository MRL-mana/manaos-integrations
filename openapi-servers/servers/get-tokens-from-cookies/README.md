# 🔐 Token Extractor API

A simple FastAPI service that extracts `oauth_id_token` and `oauth_access_token` from cookies.

## 🚀 Features

- 🔑 Parses cookies for SSO tokens from Open WebUI
- 📤 Returns the extracted tokens as JSON

## 📦 Endpoint

### GET /tokens

Reads cookies and returns:

```json
{
  "oauth_id_token": "string or null",
  "oauth_access_token": "string or null"
}
```

## ⚙️ Setup

Make sure your SSO is configured in Open WebUI and the cookies `oauth_id_token` and `oauth_access_token` are set in the client.

Run the service:

```bash
uvicorn main:app --host 0.0.0.0 --reload
```

## 🍿 Example

```bash
curl --cookie "oauth_id_token=xxx; oauth_access_token=yyy" http://127.0.0.1:8000/tokens
```

## 🧪 Tech Stack

- Python 3.11+
- FastAPI ⚡

Made with ❤️ by Open WebUI team.