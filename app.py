from fastapi import FastAPI, UploadFile, File, Form, WebSocket, BackgroundTasks, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pypdf import PdfReader
from deep_translator import GoogleTranslator
from fpdf import FPDF
import fitz  # used for pdf-to-image conversion and page count if needed (wait, pdfplumber does that)
import tempfile
import boto3
import uuid
import asyncio
import os

# ── Script-aware font registry ────────────────────────────────────────────────
# Maps script name → PyMuPDF font filename/name
SCRIPT_FONTS: dict = {}

_FONT_FILES = {
    "Devanagari": "NotoSansDevanagari-Regular.ttf",  # hi, mr
    "Bengali":    "NotoSansBengali-Regular.ttf",      # bn
    "Gujarati":   "NotoSansGujarati-Regular.ttf",     # gu
    "Gurmukhi":   "NotoSansGurmukhi-Regular.ttf",     # pa
    "Tamil":      "NotoSansTamil-Regular.ttf",        # ta
    "Telugu":     "NotoSansTelugu-Regular.ttf",       # te
    "Kannada":    "NotoSansKannada-Regular.ttf",      # kn
    "Malayalam":  "NotoSansMalayalam-Regular.ttf",    # ml
    "Arabic":     "NotoSansArabic-Regular.ttf",       # ar, ur
    "Cyrillic":   "NotoSans-Regular.ttf",             # ru
}

def _register_fonts_startup():
    for script, filename in _FONT_FILES.items():
        if os.path.exists(filename):
            SCRIPT_FONTS[script] = filename
            print(f"[fonts] OK  {script} ({filename})")
        else:
            print(f"[fonts] MISSING {filename} — {script} will use fallback")
    _arial = "/Library/Fonts/Arial Unicode.ttf"
    if not os.path.exists(_arial):
        _arial = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    if os.path.exists(_arial):
        for script in ("CJK_SC", "CJK_JP", "CJK_KR"):
            SCRIPT_FONTS[script] = _arial
        print(f"[fonts] OK  CJK_SC/JP/KR (Arial Unicode: {_arial})")
    else:
        for script in ("CJK_SC", "CJK_JP", "CJK_KR"):
            SCRIPT_FONTS[script] = "cjk"
        print(f"[fonts] OK  CJK (using fitz builtin 'cjk')")

_register_fonts_startup()


def draw_mixed_text(pdf_out, text: str, x: float, y: float, font_size: float,
                    fallback_font: str = "helv"):
    """Draw text switching fonts automatically per Unicode block using fpdf2."""
    if not text:
        return

    def _font_for(ch: str) -> str:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F or 0xA8E0 <= cp <= 0xA8FF:
            return SCRIPT_FONTS.get("Devanagari", fallback_font)
        if 0x0980 <= cp <= 0x09FF:
            return SCRIPT_FONTS.get("Bengali", fallback_font)
        if 0x0A00 <= cp <= 0x0A7F:
            return SCRIPT_FONTS.get("Gurmukhi", fallback_font)
        if 0x0A80 <= cp <= 0x0AFF:
            return SCRIPT_FONTS.get("Gujarati", fallback_font)
        if 0x0B80 <= cp <= 0x0BFF:
            return SCRIPT_FONTS.get("Tamil", fallback_font)
        if 0x0C00 <= cp <= 0x0C7F:
            return SCRIPT_FONTS.get("Telugu", fallback_font)
        if 0x0C80 <= cp <= 0x0CFF:
            return SCRIPT_FONTS.get("Kannada", fallback_font)
        if 0x0D00 <= cp <= 0x0D7F:
            return SCRIPT_FONTS.get("Malayalam", fallback_font)
        if (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or
                0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF):
            return SCRIPT_FONTS.get("Arabic", fallback_font)
        if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            return SCRIPT_FONTS.get("CJK_KR", fallback_font)
        if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            return SCRIPT_FONTS.get("CJK_JP", fallback_font)
        if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or
                0xF900 <= cp <= 0xFAFF):
            return SCRIPT_FONTS.get("CJK_SC", fallback_font)
        if 0x3000 <= cp <= 0x303F or 0x3200 <= cp <= 0x33FF:
            return SCRIPT_FONTS.get("CJK_SC", SCRIPT_FONTS.get("CJK_JP", fallback_font))
        if 0xFF00 <= cp <= 0xFFEF:
            return SCRIPT_FONTS.get("CJK_SC", SCRIPT_FONTS.get("CJK_JP", fallback_font))
        if 0x0400 <= cp <= 0x04FF:
            return SCRIPT_FONTS.get("Cyrillic", fallback_font)
        if cp > 127:
            return SCRIPT_FONTS.get("ArialUnicode", fallback_font)
        return fallback_font

    segments, cur_font, cur_chunk = [], None, ""
    for ch in text:
        f = _font_for(ch)
        if f != cur_font:
            if cur_chunk:
                segments.append((cur_font, cur_chunk))
            cur_font, cur_chunk = f, ch
        else:
            cur_chunk += ch
    if cur_chunk:
        segments.append((cur_font, cur_chunk))

    # Identify if the whole line is mostly Devanagari for shaping hints
    is_deva = any(0x0900 <= ord(c) <= 0x097F for c in text)

    cursor_x = x
    for seg_font, seg_text in segments:
        if seg_font and seg_font.endswith(".ttf"):
            font_id = os.path.basename(seg_font).split(".")[0]
            try:
                if font_id.lower() not in pdf_out.fonts:
                    pdf_out.add_font(font_id, fname=seg_font)
                pdf_out.set_font(font_id, size=font_size)
                
                # Apply explicit script shaping for Devanagari to ensure matra joining
                if "Devanagari" in seg_font or is_deva:
                    pdf_out.set_text_shaping(True, script="deva", language="hin")
                else:
                    pdf_out.set_text_shaping(True) # generic
            except Exception:
                pdf_out.set_font("helvetica", size=font_size)
        else:
            pdf_out.set_font("helvetica", size=font_size)
            pdf_out.set_text_shaping(False) # no shaping for standard fonts if not needed
        
        pdf_out.text(x=cursor_x, y=y, text=seg_text)
        cursor_x += pdf_out.get_string_width(seg_text)

from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
import auth
import email_utils

# Create database tables if they do not exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# store progress of each task
progress_store = {}

# AWS S3 setup
s3 = boto3.client("s3", region_name="eu-north-1")
BUCKET_NAME = "pdf-translator-storage"

# CORS config
# On Render, set ALLOWED_ORIGIN to your GitHub Pages URL (e.g., https://jayesh5103.github.io)
_allowed_origins = os.environ.get("ALLOWED_ORIGIN", "*").split(",")
_allowed_origins = [o.strip() for o in _allowed_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True if "*" not in _allowed_origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Home Route
# ---------------------------

# Duplicate home() route removed

# ---------------------------
# WebSocket Progress Endpoint
# ---------------------------

from fastapi import WebSocketDisconnect

@app.websocket("/progress/{task_id}")
async def progress_socket(websocket: WebSocket, task_id: str):

    await websocket.accept()

    try:
        while True:

            progress = progress_store.get(task_id, 0)

            await websocket.send_json({"progress": progress})

            if progress >= 100 or progress < 0:
                break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        print(f"WebSocket error for task {task_id}: {e}")

# ---------------------------
# Auth API Endpoints
# ---------------------------
from fastapi.security import OAuth2PasswordRequestForm

class UserCreate(auth.User):
    pass # Pydantic model for validation (Wait, we need a Pydantic model)

from pydantic import BaseModel, EmailStr
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/login")
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

from datetime import datetime

class ForgotPasswordRequest(BaseModel):
    email: str

@app.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        return {"message": "If that email exists, an OTP has been sent to it."}
    
    # Generate 6-digit OTP
    import random
    otp = str(random.randint(100000, 999999))
    
    user.reset_token = otp
    user.reset_token_expiry = datetime.utcnow() + auth.timedelta(minutes=10)  # OTP valid for 10 mins
    db.commit()

    # Send OTP via email in background
    background_tasks.add_task(email_utils.send_reset_password_email, req.email, otp)

    return {"message": "A 6-digit OTP has been sent to your email. It expires in 10 minutes."}

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str

@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == request.email,
        models.User.reset_token == request.reset_token
    ).first()
    
    if not user or user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Update password and clear token
    user.password_hash = auth.get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()
    
    return {"message": "Password has been successfully reset. You can now log in."}

class ForgotUsernameRequest(BaseModel):
    email: str

@app.post("/forgot-username")
@limiter.limit("5/minute")
def forgot_username(request: Request, req: ForgotUsernameRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        return {"message": "If that email is registered, your username has been sent to it."}

    background_tasks.add_task(email_utils.send_forgot_username_email, req.email, user.username)

    return {"message": "If that email is registered, your username has been sent to it."}


# ---------------------------
# Send PDF via Email
# ---------------------------


class SendPdfRequest(BaseModel):
    recipient_email: EmailStr
    download_url: str
    filename: str

@app.post("/send-pdf")
@limiter.limit("5/minute")
def send_pdf(request: Request, req: SendPdfRequest, background_tasks: BackgroundTasks,
             current_user: models.User = Depends(auth.get_current_user)):
    """Fetch the translated PDF from S3 and email it as an attachment to any recipient."""
    def _do_send():
        try:
            import requests as _req
            resp = _req.get(req.download_url, timeout=30)
            resp.raise_for_status()
            pdf_bytes = resp.content
            email_utils.send_pdf_email(
                recipient_email=req.recipient_email,
                filename=req.filename,
                pdf_bytes=pdf_bytes,
            )
        except Exception as e:
            print(f"[send-pdf] Error: {e}")

    background_tasks.add_task(_do_send)
    return {"message": f"PDF is being sent to {req.recipient_email}. It should arrive in a few seconds!"}


# ---------------------------
# History API Endpoint
# ---------------------------

@app.get("/history")
def get_history(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    tasks = db.query(models.TranslationTask).filter(models.TranslationTask.user_id == current_user.id).order_by(models.TranslationTask.created_at.desc()).all()
    return tasks

# ---------------------------
# Admin API Endpoints
# ---------------------------

from fastapi import Header

def verify_admin(x_admin_secret: str = Header(...)):
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    real_secret = os.environ.get("ADMIN_SECRET")
    if not real_secret or x_admin_secret != real_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    return True

@app.get("/admin/stats")
def get_admin_stats(db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    total_users = db.query(models.User).count()
    total_tasks = db.query(models.TranslationTask).count()
    completed_tasks = db.query(models.TranslationTask).filter(models.TranslationTask.status == "completed").count()
    failed_tasks = db.query(models.TranslationTask).filter(models.TranslationTask.status == "failed").count()
    processing_tasks = db.query(models.TranslationTask).filter(models.TranslationTask.status == "processing").count()
    return {
        "users": total_users,
        "translations_total": total_tasks,
        "translations_completed": completed_tasks,
        "translations_failed": failed_tasks,
        "translations_processing": processing_tasks
    }

@app.get("/admin/users")
def get_admin_users(db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    from sqlalchemy import func
    # Get users with their translation counts
    users = db.query(
        models.User.id,
        models.User.username,
        models.User.email,
        func.count(models.TranslationTask.id).label('task_count')
    ).outerjoin(
        models.TranslationTask, models.User.id == models.TranslationTask.user_id
    ).group_by(models.User.id).all()
    
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "task_count": u.task_count
        } for u in users
    ]

# ---------------------------
# Translate PDF Process (Background)
# ---------------------------

def _translate_with_retry(text: str, target_language: str, max_retries: int = 2) -> str:
    """Translate text to target_language with retry logic.
    Returns the translated string, or the original text on failure."""
    import time
    if not text or not text.strip():
        return text
    for attempt in range(max_retries + 1):
        try:
            result = GoogleTranslator(source="auto", target=target_language).translate(text)
            if result and result.strip():
                # Normalise whitespace artifacts Google sometimes introduces
                return " ".join(result.split())
        except Exception as e:
            print(f"[translate] attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(0.5)
    return text  # fall back to original on total failure


def _is_label_value_line(label: str) -> bool:
    """Return True only when the left side of a colon looks like a plain label.
    Guards against splitting URLs, timestamps, ratios, codes, etc."""
    label = label.strip()
    # Labels are short (≤40 chars), have no digits, and no '/' or '.' sequences
    if len(label) > 40:
        return False
    if any(ch.isdigit() for ch in label):
        return False
    if '/' in label or '..' in label:
        return False
    return True


def process_translation(input_path: str, language: str, task_id: str, file_key: str):
    import pdfplumber
    import fitz
    import os

    # We create our own DB session here because it's a background task
    from database import SessionLocal
    db = SessionLocal()

    try:
        output_path = f"translated_{task_id}.pdf"
        
        image_temp_files = []

        with pdfplumber.open(input_path) as pdf:
            total_pages = len(pdf.pages)
            first_page = pdf.pages[0]
            
            # Using 'pt' to match pdfplumber's coordinates
            pdf_out = FPDF(unit="pt", format=(first_page.width, first_page.height))
            # Explicitly enable text shaping via uharfbuzz
            pdf_out.set_text_shaping(True)
            
            for page_index, page in enumerate(pdf.pages):
                current_page_num = page_index + 1
                
                if page_index > 0:
                    pdf_out.add_page(format=(page.width, page.height))
                else:
                    pdf_out.add_page()
                
                # --- PROCESS IMAGES ---
                for img in page.images:
                    try:
                        # Extract image bounding box using page cropping
                        bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                        cropped_page = page.within_bbox(bbox)
                        img_obj = cropped_page.to_image(resolution=200)
                        
                        # Save temp image
                        import tempfile
                        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        img_obj.save(temp_img.name, format="PNG")
                        temp_img.close()
                        image_temp_files.append(temp_img.name)
                        
                        pdf_out.image(temp_img.name, x=img["x0"], y=img["top"], w=img["width"], h=img["height"])
                    except Exception as e:
                        print(f"Failed to process image on page {current_page_num}: {e}")
                
                # --- PROCESS TEXT ---
                # Using extract_text_lines() is much better at preserving spaces.
                # Adding x_tolerance=2 ensures narrow gaps become spaces.
                text_lines = page.extract_text_lines(layout=True, x_tolerance=2)

                # Now we translate and draw each line
                for line in text_lines:
                    full_text = line["text"].strip()
                    if not full_text: continue

                    # Estimate font size from bbox if not available, but usually it is 12
                    font_size = 12
                    # Try to find font size from characters in the line
                    line_chars = [c for c in page.chars if c["top"] >= line["top"] and c["bottom"] <= line["bottom"]]
                    if line_chars:
                        font_size = sum(c["size"] for c in line_chars) / len(line_chars)

                    start_x = line["x0"]
                    baseline_y = line["bottom"]
                    
                    # Split label : value only when the left-hand side is a plain
                    # short label (not a URL, timestamp, code, etc.)
                    if ":" in full_text:
                        parts = full_text.split(":", 1)
                        label = parts[0].strip()
                        value = parts[1].strip()

                        if _is_label_value_line(label):
                            # Translate label and value independently for best accuracy
                            translated_label = _translate_with_retry(label, language)
                            translated_val   = _translate_with_retry(value, language) if value else ""
                            full_translated  = translated_label + " : " + translated_val
                        else:
                            # Treat the whole line as a single unit
                            full_translated = _translate_with_retry(full_text, language)

                        draw_mixed_text(pdf_out, full_translated, start_x, baseline_y, font_size)
                    else:
                        # No colon — translate the whole line
                        translated_text = _translate_with_retry(full_text, language)
                        draw_mixed_text(pdf_out, translated_text, start_x, baseline_y, font_size)

                # Update Progress
                progress = int((current_page_num / total_pages) * 90)
                progress_store[task_id] = progress
                print(f"Progress: {progress}%")

            # Finalize PDF
            pdf_out.output(output_path)
            
        # Cleanup image temp files
        for tmp_img in image_temp_files:
            try:
                os.remove(tmp_img)
            except:
                pass

        # Upload to S3
        progress_store[task_id] = 95
        s3.upload_file(
            output_path,
            BUCKET_NAME,
            file_key,
            ExtraArgs={
                "ContentType": "application/pdf"
            }
        )

        try:
            os.remove(output_path)
            os.remove(input_path)
        except:
            pass

        progress_store[task_id] = 100
        print("Translation complete!")
        
        # Update Task Status in DB
        task_record = db.query(models.TranslationTask).filter(models.TranslationTask.id == task_id).first()
        if task_record:
            task_record.status = "completed"
            
            # Generate permanent download URL
            file_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": file_key
                },
                ExpiresIn=3600 * 24 * 7 # 7 days
            )
            task_record.download_url = file_url
            db.commit()
            
    except Exception as e:
        print(f"Translation Error: {e}")
        progress_store[task_id] = -1
        task_record = db.query(models.TranslationTask).filter(models.TranslationTask.id == task_id).first()
        if task_record:
            task_record.status = "failed"
            db.commit()
    finally:
        db.close()

# ---------------------------
# Translate PDF API Upload
# ---------------------------

@app.post("/translate")
async def translate_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    if file.content_type not in ("application/pdf", "application/octet-stream") and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()

    # Validate file size (max 20 MB)
    MAX_SIZE = 20 * 1024 * 1024
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum allowed size is 20 MB.")

    # Quick PDF magic-byte check
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(contents)
        input_path = temp.name

    task_id = str(uuid.uuid4())
    file_key = f"translated/{task_id}.pdf"

    # generate secure initial download link
    file_url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": file_key
        },
        ExpiresIn=3600
    )

    # Save initial task to DB
    new_task = models.TranslationTask(
        id=task_id,
        user_id=current_user.id,
        original_filename=file.filename,
        target_language=language,
        status="processing"
    )
    db.add(new_task)
    db.commit()

    background_tasks.add_task(
        process_translation,
        input_path=input_path,
        language=language,
        task_id=task_id,
        file_key=file_key
    )

    return {
        "task_id": task_id,
        "download_url": file_url
    }

# ── Serve frontend static files (at the end to avoid shadowing API) ───────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

# Serve specific HTML files from root for easier deployment
@app.get("/", include_in_schema=False)
async def serve_root():
    if os.path.exists("login.html"):
        return FileResponse("login.html")
    return {"message": "Worldocs API Running"}

@app.get("/index", include_in_schema=False)
async def index_redirect():
    return RedirectResponse(url="/index.html")

@app.get("/login", include_in_schema=False)
async def login_redirect():
    return RedirectResponse(url="/login.html")

@app.get("/dashboard", include_in_schema=False)
async def dashboard_redirect():
    return RedirectResponse(url="/dashboard.html")

@app.get("/{filename}", include_in_schema=False)
async def serve_static_root(filename: str):
    # List of allowed static file extensions
    allowed_extensions = {".css", ".js", ".ttf", ".png", ".jpg", ".jpeg", ".svg", ".pdf", ".ico"}
    _, ext = os.path.splitext(filename)
    
    if ext.lower() in allowed_extensions:
        if os.path.exists(filename):
            return FileResponse(filename)
            
    # Also handle .html if requested explicitly or without extension
    if filename.endswith(".html") or not ext:
        html_path = filename if filename.endswith(".html") else f"{filename}.html"
        if os.path.exists(html_path):
            return FileResponse(html_path)
        
    raise HTTPException(status_code=404)

# If the user has a 'frontend' directory, mount it.
if os.path.isdir("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")