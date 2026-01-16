from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import json

app = FastAPI(
    title="Simple Flashcard Display API",
    version="1.0.0",
    description="A simple tool for AI to display interactive flashcards.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# -------------------------------
# Pydantic models
# -------------------------------


class Flashcard(BaseModel):
    front: str = Field(..., description="Front of the flashcard (question/prompt)")
    back: str = Field(..., description="Back of the flashcard (answer/explanation)")


class FlashcardSet(BaseModel):
    title: str = Field("Flashcards", description="Title for the flashcard set")
    cards: List[Flashcard] = Field(..., description="List of flashcards")
    description: Optional[str] = Field(None, description="Optional description")


# -------------------------------
# HTML Template
# -------------------------------


def flashcard_html(title: str, cards: List[dict], description: str = None) -> str:
    cards_json = json.dumps(cards)
    desc_html = f"<p class='description'>{description}</p>" if description else ""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <style>
        html {{
            height: 45rem;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
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
            margin-bottom: 10px;
            font-size: 2rem;
        }}
        .description {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
        }}
        .card {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 40px;
            margin: 20px 0;
            min-height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.1);
            border-color: #667eea;
        }}
        .card.flipped {{
            background: #667eea;
            color: white;
        }}
        .card-content {{
            font-size: 1.2rem;
            line-height: 1.6;
        }}
        .controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 30px 0;
            padding: 0 10px;
        }}
        .btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}
        .btn:hover {{
            background: #5a6fd8;
            transform: translateY(-2px);
        }}
        .btn:disabled {{
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
        }}
        .counter {{
            font-size: 1.1rem;
            color: #7f8c8d;
            font-weight: 500;
        }}
        .hint {{
            text-align: center;
            color: #95a5a6;
            margin-top: 10px;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container" x-data="flashcards()">
        <h1>{title}</h1>
        {desc_html}
        
        <div class="card" 
             :class="{{flipped: isFlipped}}" 
             @click="flip()">
            <div class="card-content" x-text="currentContent"></div>
        </div>
        
        <div class="hint" x-show="!isFlipped">
            💡 Click card to reveal answer
        </div>
        
        <div class="controls">
            <button class="btn" 
                    @click="prev()" 
                    :disabled="currentIndex === 0">
                ← Previous
            </button>
            
            <div class="counter">
                <span x-text="currentIndex + 1"></span> / <span x-text="cards.length"></span>
            </div>
            
            <button class="btn" 
                    @click="next()" 
                    :disabled="currentIndex === cards.length - 1">
                Next →
            </button>
        </div>
    </div>

    <script>
        function flashcards() {{
            return {{
                cards: {cards_json},
                currentIndex: 0,
                isFlipped: false,
                
                get currentCard() {{
                    return this.cards[this.currentIndex] || {{}};
                }},
                
                get currentContent() {{
                    return this.isFlipped ? this.currentCard.back : this.currentCard.front;
                }},
                
                flip() {{
                    this.isFlipped = !this.isFlipped;
                }},
                
                next() {{
                    if (this.currentIndex < this.cards.length - 1) {{
                        this.currentIndex++;
                        this.isFlipped = false;
                    }}
                }},
                
                prev() {{
                    if (this.currentIndex > 0) {{
                        this.currentIndex--;
                        this.isFlipped = false;
                    }}
                }}
            }}
        }}
    </script>
</body>
</html>
    """


# -------------------------------
# Routes
# -------------------------------


@app.post("/display", summary="Display flashcards")
def display_flashcards(flashcard_set: FlashcardSet):
    """Display a set of flashcards in an interactive HTML interface."""
    if not flashcard_set.cards:
        raise HTTPException(status_code=400, detail="No flashcards provided")

    cards_dict = [
        {"front": card.front, "back": card.back} for card in flashcard_set.cards
    ]

    html_content = flashcard_html(
        title=flashcard_set.title,
        cards=cards_dict,
        description=flashcard_set.description,
    )

    headers = {"Content-Disposition": "inline"}

    return HTMLResponse(content=html_content, headers=headers)


@app.get("/", summary="Home page")
def home():
    """Simple home page with instructions."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flashcard Display Tool</title>
        <style>
            body {
                font-family: system-ui, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                line-height: 1.6;
                color: #333;
                height: 50rem;
            }
            .example {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>🃏 Flashcard Display Tool</h1>
        <p>This is a simple tool for AI assistants to display interactive flashcards.</p>
        
        <h2>Usage</h2>
        <p>POST to <code>/display</code> with JSON data:</p>
        
        <div class="example">
            <pre>{
  "title": "My Flashcards",
  "description": "Practice questions",
  "cards": [
    {
      "front": "What is 2 + 2?",
      "back": "4"
    },
    {
      "front": "Capital of France?",
      "back": "Paris"
    }
  ]
}</pre>
        </div>
        
        <p>Features:</p>
        <ul>
            <li>Click cards to flip and reveal answers</li>
            <li>Navigate with Previous/Next buttons</li>
            <li>Clean, responsive design</li>
            <li>Perfect for AI-generated content</li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
