from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from gtts import gTTS
from googletrans import Translator
from cryptography.fernet import Fernet
import tempfile
import logging
import os
import openai

app = FastAPI()

# Configure Logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Encryption Key for Audio
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# OpenAI API Key
openai.api_key = "your-openai-api-key"

# Language Mapping
LANGUAGE_MAPPING = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "tr": "Turkish"
}

# Serve static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="."), name="static")

# Root Route to Serve the HTML File
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r") as file:
        return HTMLResponse(content=file.read())

# Enhance Transcription with OpenAI
def enhance_transcription(text: str):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Enhance the following medical transcription for accuracy: {text}",
            max_tokens=100,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logging.error(f"Error enhancing transcription: {e}")
        return text  # Fallback to original text if enhancement fails

# Translate and Speak Endpoint
@app.post("/translate/")
async def translate_and_speak(
    text: str = Form(...),
    input_lang_code: str = Form(...),
    output_lang_code: str = Form(...)
):
    try:
        # Validate language codes
        if input_lang_code not in LANGUAGE_MAPPING or output_lang_code not in LANGUAGE_MAPPING:
            return JSONResponse({"error": "Invalid language code"}, status_code=400)

        # Enhance transcription using OpenAI
        enhanced_text = enhance_transcription(text)

        # Translate Text
        translator = Translator()
        translated_text = translator.translate(enhanced_text, src=input_lang_code, dest=output_lang_code).text

        # Generate Audio
        tts = gTTS(translated_text, lang=output_lang_code)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            tts.save(temp_audio.name)

            # Encrypt the file
            with open(temp_audio.name, "rb") as file:
                encrypted_data = cipher.encrypt(file.read())
            with open(temp_audio.name, "wb") as file:
                file.write(encrypted_data)

            # Return the file path (temporary for now)
            return JSONResponse({
                "original_text": enhanced_text,
                "translated_text": translated_text,
                "audio_file": temp_audio.name
            })

    except Exception as e:
        logging.error(f"Error during translation: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# Serve Audio Endpoint
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    try:
        # Decrypt and serve audio file
        decrypted_path = f"decrypted_{filename}"
        with open(filename, "rb") as file:
            encrypted_data = file.read()
        with open(decrypted_path, "wb") as file:
            file.write(cipher.decrypt(encrypted_data))

        # Serve the file and clean up afterward
        response = FileResponse(decrypted_path, media_type="audio/mp3")
        os.remove(decrypted_path)  # Clean up the decrypted file
        os.remove(filename)  # Clean up the original encrypted file
        return response
    except Exception as e:
        logging.error(f"Error decrypting audio: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
