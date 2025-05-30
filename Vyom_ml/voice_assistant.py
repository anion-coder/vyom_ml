from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import tts_with_llm
import io
import wave
import logging
import os
from typing import Optional
from config import settings
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Banking Assistant API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process_audio/")
async def process_audio(
    target_lang: str = Form(...),
    audio: UploadFile = File(...),
    source_lang: Optional[str] = Form(None)
):
    """Process audio input and return AI-generated speech response."""
    try:
        # Validate language codes
        if target_lang not in settings.SUPPORTED_LANGUAGES.values():
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target language. Supported languages: {list(settings.SUPPORTED_LANGUAGES.values())}"
            )
        
        if source_lang and source_lang not in settings.SUPPORTED_LANGUAGES.values():
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported source language. Supported languages: {list(settings.SUPPORTED_LANGUAGES.values())}"
            )

        # Save received audio file
        audio_path = settings.TEMP_AUDIO_PATH
        try:
            with open(audio_path, "wb") as f:
                f.write(await audio.read())
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save audio file")

        # Convert speech to text
        transcribed_text = tts_with_llm.speech_to_text(audio_path)
        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Speech-to-text conversion failed")

        logger.info(f"Transcribed text: {transcribed_text}")

        # Process AI response
        ai_response = tts_with_llm.chat_func(transcribed_text)
        if not ai_response:
            raise HTTPException(status_code=500, detail="AI processing failed")

        logger.info(f"AI Response: {ai_response}")

        # Translate AI response if needed
        translated_response = tts_with_llm.translate_text(
            ai_response, 
            source_lang or "en-IN", 
            target_lang
        )
        if not translated_response:
            raise HTTPException(status_code=500, detail="Translation failed")

        # Convert AI response to speech
        tts_audio = tts_with_llm.text_to_speech(translated_response, target_lang)
        if not tts_audio:
            raise HTTPException(status_code=500, detail="Text-to-speech conversion failed")

        # Clean up temporary file
        try:
            os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {str(e)}")

        # Return AI-generated speech
        return StreamingResponse(
            io.BytesIO(tts_audio),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="response_{target_lang}.wav"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "supported_languages": settings.SUPPORTED_LANGUAGES}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)