---
name: voice-ai-engineering
description: Build and debug end-to-end speech pipelines with Whisper-style models and ffmpeg - ingestion and validation, preprocessing, transcription, speaker diarization, transcript cleanup, SRT/VTT generation, and structured handoff. Use when transcribing audio, wiring TTS/ASR stages, fixing WER or timing drift, chunking long recordings, or producing subtitles and speaker-attributed transcripts.
---

# Voice AI Integration Engineer

Turn raw audio into clean, structured, time-stamped, speaker-attributed text -
and keep the pipeline degrading gracefully on noisy, multi-speaker, or long-form
input instead of only working on clean studio recordings.

## Pipeline stages

1. **Ingest and validate.** Never trust extensions: probe the container with
   `ffprobe -print_format json -show_streams -show_format` and reject the file if
   duration is unknown/non-positive/oversized, or no audio stream exists. Record
   codec, sample rate, channel count for the run log.
2. **Preprocess.** Whisper-style models want **16 kHz mono** unless the model
   documents otherwise. Extract the audio track explicitly (never assume an `.mp4`
   is audio-only), downmix to mono, decode to 16-bit PCM:

   ```bash
   ffmpeg -y -i in.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 \
     -af "loudnorm=I=-16:TP=-1.5:LRA=11" out.wav
   ```

   Keep the original file untouched; write preprocessed audio to a scratch area.
3. **Chunk long audio.** Do not rely on the model's maximum input duration -
   overflow truncates silently. Chunk (30 min is a sane default) with a small
   overlap (about 30 s) and merge with overlap trimming so no word is lost at
   boundaries.
4. **Transcribe.** `faster-whisper` (CTranslate2) for GPU/CPU speed, `whisper.cpp`
   for CPU-only boxes, cloud ASR (OpenAI, Deepgram, AssemblyAI...) when accuracy,
   diarization quality, or volume justifies it and privacy allows. Pick model size
   (tiny -> large-v3) from the latency/accuracy budget; keep `word_timestamps=True`
   when downstream timing matters.
5. **Diarize (when speakers matter).** `pyannote.audio` or ASR-native diarization;
   merge speaker turns with transcription segments by time overlap. Preserve
   speaker attribution through every later stage - stripping labels breaks all
   downstream consumers.
6. **Post-process.** Never treat model punctuation/capitalization as ground truth -
   run a normalization pass; do not conflate confidence scores with accuracy (flag
   low-confidence segments for human review instead of deleting them); format
   timestamps (word/segment level) and emit SRT/VTT/ASS with sane line lengths and
   reading speed.
7. **Hand off.** Deliver structured JSON (segments with start/end/speaker/text),
   subtitles, and a Markdown reading copy. Downstream consumers (summarizers,
   TTS dubbing, CMS, editors) must receive normalized, correctly attributed text -
   plus a small run report (model, parameters, WER sample if measurable, gaps).

## Hard rules

- **Never discard timestamps.** Regenerating them costs a full re-transcription.
- **16 kHz mono before the model**, unless the model documents otherwise; bad or
  unvalidated input is the leading cause of silent accuracy loss.
- **Chunk explicitly** - overflow is silent and corrupts output without error.
- **Keep raw audio and unredacted transcripts out of logs**; redact PII as a named,
  configurable stage, and honor retention windows.
- **Verified means executed** (§6): WER, alignment, and loudness claims come from
  measurements on the actual output, not from the model's reputation.
- Fluency is not accuracy: verify names, numbers, and domain terms against a
  sample of the audio (spot-check by listening or by waveform-aligned segments).

## Debugging quick table

| Symptom | Usual cause |
|---|---|
| Uniform garbage / hallucinated repetitions | wrong sample rate or channels (not 16 kHz mono) |
| Words missing at regular intervals | chunk boundaries without overlap |
| Slow drift over a long file | chunk timestamps not re-anchored on merge |
| One speaker split into several | diarization run on unnormalized audio |
| Punctuation noise / casing chaos | model output taken as ground truth, no normalization pass |
| Trailing silence kills timing | no silence trim before transcription |

## Deliverable template

```markdown
## Transcription run
Input: <file, duration, codec, sample rate/channels probed>
Preprocess: <commands applied>
Model: <engine, model size, device, language, key parameters>
Chunks: <count, overlap, merge strategy>
Diarization: <method, speaker count, merge tolerance>
Outputs: <transcript.json (segments), subtitles.srt/.vtt, reading copy.md>
Verification: <spot-check results, WER sample, timing spot-checks, exit codes>
Known gaps: <low-confidence ranges flagged for review>
```
