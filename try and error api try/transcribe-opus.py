#!/usr/bin/env python3
"""
Local Whisper transcription helper for Node server.

Usage:
  python transcribe-opus.py <audio_path> [model] [language]

- <audio_path>: Path to audio file (.opus, .mp3, .wav, etc.)
- [model]: Whisper model name (tiny, base, small, medium, large). Default: base
- [language]: Language code (e.g., en, es) or 'auto' to auto-detect. Default: en

Outputs created next to <audio_path> (replacing extension):
  - .json  Detailed JSON (text, language, segments with timestamps)
  - .txt   Plain text transcript
  - .srt   SubRip subtitle file

Notes:
  - Requires Python, FFmpeg, and openai-whisper (`pip install openai-whisper`).
  - On first run for a model, the model weights will download (can be large).
  - Designed to match server.js expectations in this project.
"""

import sys
import os
import json
import math

def format_timestamp(seconds: float) -> str:
    if seconds is None:
        seconds = 0.0
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int(round((secs - int(secs)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"

def write_srt(segments, srt_path: str) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.get('start', 0))
        end = format_timestamp(seg.get('end', 0))
        text = seg.get('text', '').strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines).strip() + "\n")

def main() -> int:
    try:
        try:
            import whisper  # openai-whisper
        except Exception as e:
            sys.stderr.write("Whisper not installed. Install with: pip install openai-whisper\n")
            raise

        if len(sys.argv) < 2:
            sys.stderr.write("Usage: python transcribe-opus.py <audio_path> [model] [language]\n")
            return 2

        audio_path = sys.argv[1]
        model_name = sys.argv[2] if len(sys.argv) >= 3 and sys.argv[2] else 'base'
        language = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[3] else 'en'

        if not os.path.isfile(audio_path):
            sys.stderr.write(f"Input file not found: {audio_path}\n")
            return 2

        base_noext, _ = os.path.splitext(audio_path)
        json_path = base_noext + '.json'
        txt_path = base_noext + '.txt'
        srt_path = base_noext + '.srt'

        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)

        # If language is 'auto', let Whisper detect language by not passing it
        transcribe_kwargs = {
            'fp16': False,  # safer on CPU/Windows
            'verbose': False,
        }
        if language and language.lower() != 'auto':
            transcribe_kwargs['language'] = language

        print(f"Transcribing: {os.path.basename(audio_path)}")
        result = model.transcribe(audio_path, **transcribe_kwargs)

        # Ensure expected keys
        text = (result.get('text') or '').strip()
        lang = result.get('language') or (language if language and language.lower() != 'auto' else None)
        segments = result.get('segments') or []

        # Write TXT
        with open(txt_path, 'w', encoding='utf-8') as f_txt:
            f_txt.write(text + ("\n" if text and not text.endswith("\n") else ""))

        # Write JSON
        to_write = {
            'text': text,
            'language': lang,
            'segments': [
                {
                    'id': seg.get('id'),
                    'start': seg.get('start'),
                    'end': seg.get('end'),
                    'text': (seg.get('text') or '').strip(),
                    'avg_logprob': seg.get('avg_logprob'),
                    'no_speech_prob': seg.get('no_speech_prob'),
                    'temperature': seg.get('temperature'),
                }
                for seg in segments
            ],
        }
        with open(json_path, 'w', encoding='utf-8') as f_json:
            json.dump(to_write, f_json, ensure_ascii=False)

        # Write SRT
        write_srt(segments, srt_path)

        # Console summary
        duration = 0.0
        if segments:
            last_end = segments[-1].get('end')
            try:
                duration = float(last_end) if last_end is not None else 0.0
            except Exception:
                duration = 0.0
        print(f"Saved transcript: {os.path.basename(txt_path)}")
        print(f"Saved JSON: {os.path.basename(json_path)}")
        print(f"Saved SRT: {os.path.basename(srt_path)}")
        print("============================================================")
        print("TRANSCRIPTION RESULT:")
        print("============================================================")
        print(text)
        print("============================================================")
        print(f"Detected language: {lang}")
        print(f"Duration: {duration:.1f} seconds")
        print("Transcription complete!")

        return 0

    except Exception as e:
        # Print the full error to stderr so Node can capture it
        sys.stderr.write(str(e) + "\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())

