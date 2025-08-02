import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any

# LangChain and Gemini imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# PDF extraction utilities
from pdf_processor import extract_text_from_pdf, save_extracted_text_to_csv

# Load environment variables
load_dotenv()

# --- FastAPI Setup ---
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Gemini / LangChain Setup ---
gemini_api_key = os.getenv("GOOGLE_API_KEY")
if not gemini_api_key:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    print("Please set it in .env (e.g., GOOGLE_API_KEY=...)")
    exit()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    google_api_key=gemini_api_key,
    temperature=0.7,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a friendly and helpful AI assistant. You answer questions concisely and informatively."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# In-memory session history store
store: Dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

chain = prompt | llm

conversation_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# --- Workspace for uploads ---
WORKDIR = Path("uploaded_pdfs")
WORKDIR.mkdir(exist_ok=True)

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = "default_session"):
    await websocket.accept()
    print(f"WebSocket connected for session_id: {session_id}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received message from client ({session_id}): {data}")

            try:
                response = conversation_with_history.invoke(
                    {"input": data},
                    config={"configurable": {"session_id": session_id}}
                )
                bot_response = response.content
                print(f"Sending response to client ({session_id}): {bot_response}")
                await websocket.send_text(bot_response)
            except Exception as e:
                error_message = f"Chatbot error: {e}"
                print(error_message)
                await websocket.send_text(f"Sorry, an error occurred with the chatbot: {e}")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session_id: {session_id}")
    except Exception as e:
        print(f"WebSocket error for session_id {session_id}: {e}")

# PDF upload + extraction endpoint
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), use_ocr: bool = Form(False)):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"error": "Only PDF files are allowed."}, status_code=400)

    session_id = str(uuid.uuid4())[:8]
    pdf_path = WORKDIR / f"{session_id}_{file.filename}"
    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract text with optional OCR fallback
    extracted = extract_text_from_pdf(str(pdf_path), ocr_fallback=use_ocr)

    # Save to CSV
    csv_path = WORKDIR / f"{session_id}_{Path(file.filename).stem}.csv"
    save_extracted_text_to_csv(extracted, str(csv_path))

    return {
        "csv_filename": csv_path.name,
        "download_endpoint": f"/download-csv/{csv_path.name}"
    }

@app.get("/download-csv/{filename}")
async def download_csv(filename: str):
    file_path = WORKDIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not found."}, status_code=404)
    return FileResponse(path=str(file_path), filename=filename, media_type="text/csv")
