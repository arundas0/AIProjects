from faster_whisper import WhisperModel

# Small model = faster, good enough for a demo. Upgrade later.
_model = WhisperModel("small", device="cpu", compute_type="int8")

def transcribe_wav_file(path: str) -> str:
    """
    Transcribes a WAV audio file to text (offline).
    Returns the concatenated transcript.
    """
    segments, info = _model.transcribe(path, beam_size=5)
    text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    return " ".join(text_parts).strip()
