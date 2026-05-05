import asyncio
import io
from bot import bot
from faster_whisper import WhisperModel
from config import MODEL_NAME
import logging

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        self.model = model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        self._lock = asyncio.Lock()

    async def extract(self, file_id: str) -> str | None:
        try:
            file = await bot.get_file(file_id)
            audio_data = io.BytesIO()
            await bot.download_file(file.file_path, destination=audio_data)
            audio_data.seek(0)

            async with self._lock:
                segments, info = await asyncio.to_thread(
                self.model.transcribe,
                audio=audio_data,
                language="ru",
                beam_size=5
                )

            recognized_text = " ".join([segment.text for segment in segments])
            return recognized_text
        except Exception as e:
            logger.error(f"Не удалось распознать голосовое: {e}")
            return None

_whisper_service = None

def get_whisper_service() -> WhisperService | None:
    """Получить экземпляр сервиса"""
    global _whisper_service

    if _whisper_service is None:
        try:
            _whisper_service = WhisperService()
            logger.info("WhisperService инициализирован")
        except Exception as e:
            logger.error(f"Не удалось инициализировать WhisperService: {e}")
            return None

    return _whisper_service

