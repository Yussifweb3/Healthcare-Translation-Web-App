import streamlit as st
import speech_recognition as sr
from gtts import gTTS
import tempfile
from googletrans import Translator
import logging
import os
from cryptography.fernet import Fernet
import sounddevice as sd
import wavio

# Configure Logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Generate a key for encryption (store securely for consistent usage)
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# Language Mapping
LANGUAGE_MAPPING = {
    "en - English": "en",
    "es - Spanish": "es",
    "fr - French": "fr",
    "de - German": "de",
    "zh - Chinese": "zh",
    "ar - Arabic": "ar",
    "hi - Hindi": "hi",
    "it - Italian": "it",
    "pt - Portuguese": "pt",
    "ru - Russian": "ru",
    "ja - Japanese": "ja",
    "ko - Korean": "ko",
    "tr - Turkish": "tr"
}

# Functions
def initialize_recognizer():
    """Initialize the speech recognizer."""
    return sr.Recognizer()

def record_audio(recognizer, duration=5, sample_rate=44100):
    """Record audio using sounddevice."""
    st.info("Please speak now...")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
    temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    wavio.write(temp_audio_path, audio_data, sample_rate, sampwidth=2)
    with sr.AudioFile(temp_audio_path) as source:
        audio = recognizer.record(source)
    os.remove(temp_audio_path)  # Clean up the temporary audio file
    return audio

def speech_to_text(audio, recognizer, input_lang_code):
    """Convert speech to text using Google Speech Recognition."""
    try:
        return recognizer.recognize_google(audio, language=input_lang_code)
    except sr.UnknownValueError:
        raise ValueError("Sorry, the audio was not clear enough to recognize.")
    except sr.RequestError as e:
        raise ConnectionError(f"Could not request results from Google Speech Recognition: {e}")

def translate_text(text, input_lang_code, output_lang_code):
    """Translate text using Google Translate."""
    translator = Translator()
    return translator.translate(text, src=input_lang_code, dest=output_lang_code).text

def text_to_speech_secure(text, output_lang_code):
    """Generate audio from text and encrypt the temporary file."""
    tts = gTTS(text, lang=output_lang_code)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        tts.save(temp_audio.name)

        # Encrypt the file
        with open(temp_audio.name, "rb") as file:
            encrypted_data = cipher.encrypt(file.read())
        with open(temp_audio.name, "wb") as file:
            file.write(encrypted_data)

        return temp_audio.name

def decrypt_audio(file_path):
    """Decrypt the encrypted audio file for playback."""
    with open(file_path, "rb") as file:
        encrypted_data = file.read()
    return cipher.decrypt(encrypted_data)

def log_error(error_message):
    """Log errors with a timestamp."""
    logging.error(error_message)

# Streamlit UI Components
def render_ui():
    """Render the main UI components."""
    st.title("Healthcare Translation Web App")
    st.subheader("Real-time multilingual translation for patients and healthcare providers")

    st.sidebar.title("Settings")
    input_lang = st.sidebar.selectbox(
        "Input Language",
        ["en - English", "es - Spanish", "fr - French", "de - German", "zh - Chinese", "ar - Arabic", "hi - Hindi", "it - Italian", "pt - Portuguese", "ru - Russian", "ja - Japanese", "ko - Korean", "tr - Turkish"]
    )
    output_lang = st.sidebar.selectbox(
        "Output Language",
        ["en - English", "es - Spanish", "fr - French", "de - German", "zh - Chinese", "ar - Arabic", "hi - Hindi", "it - Italian", "pt - Portuguese", "ru - Russian", "ja - Japanese", "ko - Korean", "tr - Turkish"]
    )

    return input_lang, output_lang

# Main Functionality
def main():
    recognizer = initialize_recognizer()
    input_lang, output_lang = render_ui()

    input_lang_code = LANGUAGE_MAPPING[input_lang]
    output_lang_code = LANGUAGE_MAPPING[output_lang]

    if st.button("Start Speaking"):
        try:
            # Record audio and convert to text
            audio = record_audio(recognizer)
            st.write("Recognizing speech...")
            original_text = speech_to_text(audio, recognizer, input_lang_code)
            st.write(f"Original Text: {original_text}")

            # Translate and convert to speech
            st.write("Translating...")
            translated_text = translate_text(original_text, input_lang_code, output_lang_code)
            st.write(f"Translated Text: {translated_text}")

            st.write("Generating audio...")
            audio_path = text_to_speech_secure(translated_text, output_lang_code)
            decrypted_audio = decrypt_audio(audio_path)

            # Play decrypted audio
            st.audio(decrypted_audio, format="audio/mp3")

            # Clean up the encrypted file after usage
            os.remove(audio_path)

        except ValueError as ve:
            st.error(str(ve))
            log_error(str(ve))
        except ConnectionError as ce:
            st.error(str(ce))
            log_error(str(ce))
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            log_error(f"Unexpected error: {e}")

# Run the app
if __name__ == "__main__":
    main()
