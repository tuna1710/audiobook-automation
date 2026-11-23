import os
import hashlib
import shutil
from contextlib import nullcontext
from .text_cleaner import clean_voice_name

_GLOBAL_TTS_ENGINE = None


def _is_tts_cache_enabled() -> bool:
    try:
        import yaml
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "configs", "app_config.yaml"
        )
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return bool(cfg.get("performance", {}).get("tts_chunk_cache", True))
    except Exception:
        pass
    return True


class TTSEngine:
    """
    Quản lý mô hình VieNeu-TTS Turbo 48kHz.
    Hỗ trợ nạp lười (Lazy loading), cache âm thanh theo hash nội dung và chạy với torch.inference_mode().
    """
    def __init__(self, model_id: str = "pnnbao-ump/VieNeu-TTS-v3-Turbo"):
        self.model_id = model_id
        self.engine = None
        self._initialize()

    def _initialize(self):
        os.environ["USE_TF"] = "0"
        os.environ["TRANSFORMERS_NO_TF"] = "1"
        os.environ["VIENEU_FUSED_FRAME"] = "0"
        try:
            from vieneu import Vieneu
            print(f"⏳ Đang khởi tạo VieNeu-TTS ({self.model_id})...")
            try:
                self.engine = Vieneu()
            except Exception as torch_err:
                print(f"⚠️ PyTorch engine gặp lỗi ({torch_err}), tự động chuyển sang backend ONNX...")
                self.engine = Vieneu(backend="onnx")
            if hasattr(self.engine, "_batch_engine") and self.engine._batch_engine is not None:
                self.engine._batch_engine.use_fused = False
            print("✅ VieNeu-TTS đã sẵn sàng hoạt động!")
        except Exception as e:
            print(f"⚠️ Cảnh báo khởi tạo VieNeu-TTS: {e}")
            self.engine = None

    def synthesize(self, text: str, voice: str, output_path: str) -> str:
        """
        Tổng hợp giọng đọc thành file âm thanh WAV (có cache nếu bật tts_chunk_cache).
        """
        actual_voice = clean_voice_name(voice)
        use_cache = _is_tts_cache_enabled()
        cache_path = None

        if use_cache:
            cache_dir = os.path.join(os.path.dirname(output_path) or "temp_work", "tts_cache")
            os.makedirs(cache_dir, exist_ok=True)
            key_hash = hashlib.sha256(f"{self.model_id}|{actual_voice}|{text}".encode("utf-8")).hexdigest()[:24]
            cache_path = os.path.join(cache_dir, f"{key_hash}.wav")
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1024:
                print(f"⚡ [TTS Cache Hit] Tái sử dụng file giọng đọc đã tổng hợp ({key_hash}.wav)")
                shutil.copyfile(cache_path, output_path)
                return output_path

        if self.engine is None:
            self._initialize()
        if self.engine is None:
            raise RuntimeError("VieNeu-TTS engine chưa được cài đặt hoặc khởi tạo thất bại.")

        try:
            import torch
            ctx = torch.inference_mode()
        except Exception:
            ctx = nullcontext()

        with ctx:
            audio_result = self.engine.infer(text=text, voice=actual_voice)
        self.engine.save(audio_result, output_path)

        if use_cache and cache_path and os.path.exists(output_path):
            try:
                shutil.copyfile(output_path, cache_path)
            except Exception:
                pass
        return output_path


def get_tts_engine() -> TTSEngine:
    global _GLOBAL_TTS_ENGINE
    if _GLOBAL_TTS_ENGINE is None:
        _GLOBAL_TTS_ENGINE = TTSEngine()
    return _GLOBAL_TTS_ENGINE


def preview_voice_sample(voice_selected: str, temp_dir: str = "temp_work") -> str:
    """
    Tạo nhanh một đoạn phát thử âm thanh cho giọng đọc được chọn.
    """
    actual_voice = clean_voice_name(voice_selected)
    preview_text = f"Xin chào, đây là giọng đọc thử nghiệm {actual_voice} trên hệ thống Studio V20."
    os.makedirs(temp_dir, exist_ok=True)
    preview_file = os.path.join(temp_dir, f"preview_{actual_voice.replace(' ', '_')}.wav")

    try:
        engine = get_tts_engine()
        return engine.synthesize(preview_text, actual_voice, preview_file)
    except Exception as e:
        print(f"⚠️ Lỗi nghe thử giọng ({actual_voice}): {e}")
        return None
