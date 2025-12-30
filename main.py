import os
import json
import time
import uvicorn
import google.generativeai as genai
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict

# --- Configuration & Security ---
app = FastAPI(title="Knowledge AI")

# SECURE: API Key from Environment
API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)

# Elite Researcher System Prompt
SYSTEM_INSTRUCTION = (
    "You are an Elite Intellectual Researcher. You analyze text, scanned documents, "
    "audio, and video with academic precision. Before answering, you must: "
    "1. Analyze the philosophical/scientific school of thought. "
    "2. Determine the specific context (Historical, Technical, or Literary). "
    "3. Synthesize answers with high cultural depth. "
    "Always return JSON for flashcard requests. Maintain an elite tone."
)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

session_db: Dict[str, Dict] = {}
templates = Jinja2Templates(directory="templates")

def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    return file

async def get_gemini_response(contents: list, history: List[Dict] = []):
    chat = model.start_chat(history=history)
    for i in range(5):
        try:
            response = await chat.send_message_async(contents)
            return response.text
        except:
            if i == 4: raise
            time.sleep(2**i)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    try:
        gemini_file = upload_to_gemini(temp_path, mime_type=file.content_type)
        session_id = "default_user"
        
        # Generate Scholarly Flashcards via Gemini
        analysis_prompt = (
            "Analyze this media. Extract 4 deep scholarly concepts as 'Flashcards'. "
            "Return ONLY a JSON array of objects: [{\"title\": \"...\", \"description\": \"...\"}]"
        )
        
        raw_response = await get_gemini_response([analysis_prompt, gemini_file])
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        
        try:
            flashcards = json.loads(clean_json)
        except:
            flashcards = [{"title": "Assimilation", "description": "The media essence has been captured."}]

        session_db[session_id] = {
            "history": [
                {"role": "user", "parts": [f"Context: {file.filename}", gemini_file]},
                {"role": "model", "parts": ["I have assimilated the media. We may begin our inquiry."]}
            ],
            "flashcards": flashcards
        }
        return {"flashcards": flashcards}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@app.post("/chat")
async def chat(query: str = Form(...)):
    session_id = "default_user"
    if session_id not in session_db:
        return JSONResponse({"error": "No media found."}, status_code=400)
    
    history = session_db[session_id]["history"]
    response_text = await get_gemini_response([query], history=history)
    
    session_db[session_id]["history"].append({"role": "user", "parts": [query]})
    session_db[session_id]["history"].append({"role": "model", "parts": [response_text]})
    
    return {"response": response_text}
