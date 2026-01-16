# 🃏 Simple Flashcard Display API
A lightweight FastAPI service to display interactive flashcards in the browser.

## 🚀 Quickstart

```bash
# Clone the repo
git clone https://github.com/open-webui/openapi-severs
cd openapi-servers/servers/flashcards

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --reload
```

Your API is now live at:
👉 `http://localhost:8000`

## 📚 Usage

Send a POST request to `/display` with JSON payload:

```json
{
  "title": "My Flashcards",
  "description": "Practice questions",
  "cards": [
    { "front": "What is 2 + 2?", "back": "4" },
    { "front": "Capital of France?", "back": "Paris" }
  ]
}
```

The server will return a clean, interactive HTML page where you can:
- Flip cards to reveal answers
- Navigate with Previous/Next buttons
- View progress with a counter

## 🌐 Endpoints
- `GET /` → Home page with instructions  
- `POST /display` → Display your flashcards  

---

Perfect for AI-generated learning tools, quizzes, or study helpers. 🎓✨