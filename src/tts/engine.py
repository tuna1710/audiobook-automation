import os
from .text_cleaner import clean_voice_name

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

    def synthesize(self, text: str, voice: str, output_path: str, speed: float = 1.0) -> str:
        """
        Tổng hợp giọng đọc thành file âm thanh WAV.
        Hỗ trợ chỉnh tốc độ đọc (speed: 0.75 - 1.50) qua FFmpeg atempo giữ nguyên cao độ giọng.
        """
        if self.engine is None:
            self._initialize()
        if self.engine is None:
            raise RuntimeError("VieNeu-TTS engine chưa được cài đặt hoặc khởi tạo thất bại.")

        actual_voice = clean_voice_name(voice)
        audio_result = self.engine.infer(text=text, voice=actual_voice)

        try:
            spd = max(0.75, min(1.50, float(speed if speed is not None else 1.0)))
        except Exception:
            spd = 1.0

        if abs(spd - 1.0) >= 0.02:
            import subprocess
            raw_tmp = f"{output_path}.raw.wav"
            self.engine.save(audio_result, raw_tmp)
            try:
                cmd = [
                    "ffmpeg", "-y", "-i", raw_tmp,
                    "-filter:a", f"atempo={spd:.2f}",
                    output_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(raw_tmp):
                    os.remove(raw_tmp)
            except Exception as spd_err:
                print(f"⚠️ Không thể chỉnh tốc độ đọc ({spd}x): {spd_err}. Dùng tốc độ gốc 1.0x.")
                if os.path.exists(raw_tmp):
                    os.replace(raw_tmp, output_path)
        else:
            self.engine.save(audio_result, output_path)

        return output_path


def get_tts_engine() -> TTSEngine:
    global _GLOBAL_TTS_ENGINE
    if _GLOBAL_TTS_ENGINE is None:
        _GLOBAL_TTS_ENGINE = TTSEngine()
    return _GLOBAL_TTS_ENGINE


def preview_voice_sample(voice_selected: str, temp_dir: str = "temp_work", speed: float = 1.0) -> str:
    """
    Tạo nhanh một đoạn phát thử âm thanh cho giọng đọc được chọn (kèm tốc độ đọc).
    """
    actual_voice = clean_voice_name(voice_selected)
    preview_text = f"Xin chào, đây là giọng đọc thử nghiệm {actual_voice} trên hệ thống Studio V20."
    os.makedirs(temp_dir, exist_ok=True)
    spd_tag = str(round(float(speed or 1.0), 2)).replace(".", "_")
    preview_file = os.path.join(temp_dir, f"preview_{actual_voice.replace(' ', '_')}_{spd_tag}.wav")

    try:
        engine = get_tts_engine()
        return engine.synthesize(preview_text, actual_voice, preview_file, speed=speed)
    except Exception as e:
        print(f"⚠️ Lỗi nghe thử giọng ({actual_voice}): {e}")
        return None
