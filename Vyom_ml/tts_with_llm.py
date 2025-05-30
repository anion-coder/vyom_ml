#update: 1) keep a global variable to store target and source language codes
# 2) update the translate_text function to accept source and target language codes as arguments
# 3) update the text_to_speech function to accept language code as an argument
# 4) update the main code to use the global language codes and pass them to the
# translate_text and text_to_speech functions
# 5) The llm function to be updated to recieve language code as input
# 6) The main code to be updated to pass the language code to the llm function



import pyaudio
import wave
import requests
import base64
import numpy as np
import simpleaudio as sa
import webrtcvad
# from llm import chat 
from llm_with_intent import create_chat_session  # Import the chat function from your banking system
from config import settings

# Remove the hardcoded API key
# SARVAM_API_KEY = "640af3fb-76f1-4a46-8f87-c1ec81108859"  # Replace with your actual key

# API Endpoints
STT_URL = "https://api.sarvam.ai/speech-to-text-translate"
TTS_URL = "https://api.sarvam.ai/text-to-speech"
trans_URL = "https://api.sarvam.ai/translate"

# Audio Config
FORMAT = pyaudio.paInt16
CHANNELS = 1  
RATE = 16000  
FRAME_DURATION_MS = 20  
CHUNK = int(RATE * (FRAME_DURATION_MS / 1000))  
SILENCE_LIMIT = RATE // CHUNK  # ~1 second of silence before stopping
AUDIO_FILE = "recorded_audio.wav"

# Initialize PyAudio and VAD
VAD = webrtcvad.Vad()
VAD.set_mode(3) # Sensitivity: 0 (strict) to 3 (sensitive)

# Set user ID for the banking system
USER_ID = "user123"  # Change this to match a valid user in your database

def record_audio():
    """Continuously listens, stops when silence is detected, and saves the recorded audio."""
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("🎤 Listening... Speak now!")
    frames = []
    silence_count = 0
    speech_detected = False

    while True:
        
        data = stream.read(CHUNK, exception_on_overflow=False)
        if not data:
            print("❌ No data received from microphone")
        
        data = np.frombuffer(data, dtype=np.int16).tobytes()  

        is_speech = VAD.is_speech(data, RATE)

        if is_speech:
            frames.append(data)
            silence_count = 0
            speech_detected = True
        elif speech_detected:
            silence_count += 1
            if silence_count > SILENCE_LIMIT:  # Stop recording after 1 sec of silence
                break

    print("🛑 Recording stopped.")

    # Stop and close streams
    stream.stop_stream()
    stream.close()
    audio.terminate() 

    # Save recorded audio
    with wave.open(AUDIO_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    print(f"✅ Audio saved as {AUDIO_FILE}")

def translate_text(text, source_lang="en-IN", target_lang="hi-IN"):
    """Converts text to another language using Sarvam Translation API."""
    payload = {
        "enable_preprocessing": False,
        "source_language_code": source_lang,
        "target_language_code": target_lang,
        "input": text,
    }
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(trans_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("translated_text", "")
    return None

def speech_to_text(audio_file):
    """Converts speech to text using Sarvam STT API."""
    headers = {"api-subscription-key": settings.SARVAM_API_KEY}
    files = {
        "file": (audio_file, open(audio_file, "rb"), "audio/wav"),
        "model": (None, "saaras:flash"),
        "with_diarization": (None, "false")
    }
    response = requests.post(STT_URL, headers=headers, files=files)

    if response.status_code == 200:
        return response.json().get("transcript", "")
    return None

def text_to_speech(text, language_code="kn-IN"):
    """Converts text to speech using Sarvam TTS API and returns decoded audio bytes."""
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": "meera",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.0,
        "speech_sample_rate": 22050,
        "enable_preprocessing": False,
        "model": "bulbul:v1",
        "override_triplets": {}
    }
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(TTS_URL, json=payload, headers=headers)

    if response.status_code == 200:
        audio_list = response.json().get("audios", [])
        if audio_list:
            return base64.b64decode(audio_list[0])  # Decode base64 to raw audio
    return None

def play_audio(audio_bytes):
    """Plays the decoded speech audio."""
    wave_obj = sa.WaveObject(audio_bytes, num_channels=1, bytes_per_sample=2, sample_rate=22050)
    print("🔊 Playing AI Response...")
    play_obj = wave_obj.play()
    play_obj.wait_done()

if __name__ == "__main__":
    print("🏦 Voice Banking Assistant Started")
    print(f"👤 User ID: {USER_ID}")
    
    target_lang = "mr-IN"
    source_lang = "mr-IN"
    
    session_id = "user123"
    groq_api_key = settings.GROQ_API_KEY
    chat_func, session_id = create_chat_session(groq_api_key, session_id)
    
    
    # Initial greeting
    greeting = chat_func("")
    translated_greeting = translate_text(greeting, "en-IN", target_lang)
    greeting_audio = text_to_speech(translated_greeting)
    if greeting_audio:
        play_audio(greeting_audio)

    while True:
        record_audio()

        # Convert speech to text (Hindi)
        transcribed_text = speech_to_text(AUDIO_FILE)
        if not transcribed_text:
            print("❌ Speech-to-text failed.")
            continue
        
        print(f"👂 You said: {transcribed_text}")
        
        # # Translate Hindi to English for the LLM
        # translated_text = translate_text(transcribed_text, source_lang, "en-IN")
        # if not translated_text:
        #     print("❌ Text translation failed.")
        #     continue
        
        print(f"🔄 Translated to English: {transcribed_text}")

        # Process with banking assistant (in English)
        llm_response = chat_func(transcribed_text)
        print(f"🤖 Assistant (English): {llm_response}")

        # Check for exit command
        if any(word in transcribed_text.lower() for word in ["exit", "quit", "bye", "goodbye"]):
            farewell = "Thank you for using our voice banking service. Goodbye!"
            translated_farewell = translate_text(farewell, "en-IN", "kn-IN")
            farewell_audio = text_to_speech(translated_farewell)
            if farewell_audio:
                play_audio(farewell_audio)
            break

        # Translate back to Hindi but keep banking terms in English
        ai_response = translate_text(llm_response, "en-IN", target_lang)
        print(f"🔄 Translated to kannada: {ai_response}")

        # Convert AI response to speech
        tts_audio = text_to_speech(ai_response)
        if not tts_audio:
            print("❌ Text-to-speech failed.")
            continue

        # Play AI-generated response
        play_audio(tts_audio)