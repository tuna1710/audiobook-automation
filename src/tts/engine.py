import os
import torch

_GLOBAL_TTS_ENGINE = None

class TTSEngine:
    """
    Quản lý mô hình VieNeu-TTS Turbo 48kHz.
    Hỗ trợ nạp lười (Lazy loading), chạy ở chế độ Eager Loop ổn định trên GPU CUDA và CPU.
    """
    def __init__(self, model_id: str = "pnnbao-ump/VieNeu-TTS-v3-Turbo"):
        self.model_id = model_id
        self.engine = None
        self._initialize()

    def _initialize(self):
        os.environ["VIENEU_FUSED_FRAME"] = "0"
        try:
            from vieneu import Vieneu
            print(f"⏳ Đang khởi tạo VieNeu-TTS ({self.model_id})...")
            self.engine = Vieneu()
            if hasattr(self.engine, "_batch_engine") and self.engine._batch_engine is not None:
                self.engine._batch_engine.use_fused = False
            print("✅ VieNeu-TTS đã sẵn sàng hoạt động!")
        except Exception as e:
            print(f"⚠️ Cảnh báo khởi tạo VieNeu-TTS: {e}")
            self.engine = None

    def synthesize(self, text: str, voice: str, output_path: str) -> str:
        """
        Tổng hợp giọng đọc thành file âm thanh WAV.
        """
        if self.engine is None:
            self._initialize()
        if self.engine is None:
            raise RuntimeError("VieNeu-TTS engine chưa được cài đặt hoặc khởi tạo thất bại.")

        audio_result = self.engine.infer(text=text, voice=voice)
        self.engine.save(audio_result, output_path)
        return output_path

def get_tts_engine() -> TTSEngine:
    global _GLOBAL_TTS_ENGINE
    if _GLOBAL_TTS_ENGINE is None:
        _GLOBAL_TTS_ENGINE = TTSEngine()
    return _GLOBAL_TTS_ENGINE
