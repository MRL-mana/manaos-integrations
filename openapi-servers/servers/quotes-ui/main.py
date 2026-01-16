from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(title="Quote Display API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class Quote(BaseModel):
    text: str
    author: str


class QuoteSet(BaseModel):
    title: str = "Quotes"
    quotes: List[Quote]


def quote_html(title: str, quotes: List[dict]) -> str:
    quote_items = ""
    for quote in quotes:
        quote_items += f"""
        <div class="quote">
            <p>"{quote['text']}"</p>
            <span>— {quote['author']}</span>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{
            font-family: system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 600px;
            width: 100%;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
        }}
        .quote {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 30px;
            margin: 20px 0;
            text-align: center;
        }}
        .quote p {{
            font-size: 1.2rem;
            font-style: italic;
            margin-bottom: 15px;
            color: #2c3e50;
        }}
        .quote span {{
            color: #667eea;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        {quote_items}
    </div>
</body>
</html>
    """


@app.post("/display")
def display_quotes(quote_set: QuoteSet):
    if not quote_set.quotes:
        raise HTTPException(status_code=400, detail="No quotes provided")

    quotes_dict = [{"text": q.text, "author": q.author} for q in quote_set.quotes]
    html_content = quote_html(quote_set.title, quotes_dict)

    headers = {"Content-Disposition": "inline"}

    return HTMLResponse(content=html_content, headers=headers)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def home():
    return HTMLResponse(
        content="""
    <html>
    <body style="font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px;">
        <h1>Quote Display Tool</h1>
        <p>POST to /display with:</p>
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px;">{
  "title": "My Quotes",
  "quotes": [
    {"text": "Hello world", "author": "Someone"}
  ]
}</pre>
    </body>
    </html>
    """
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
