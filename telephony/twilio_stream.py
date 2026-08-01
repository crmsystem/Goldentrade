"""
telephony/twilio_stream.py

Twilio entry point for the voice pipeline:

  1. Twilio calls POST /voice on an inbound call; we reply with TwiML that
     opens a bidirectional Media Stream back to our own WS /media endpoint,
     forwarding the caller's phone number as a custom stream parameter.
  2. Twilio streams 8 kHz mu-law audio frames over that websocket. Each frame
     is decoded, upsampled to 16 kHz PCM16, and handed to the shared
     CallSession (Silero VAD -> STT -> LLM -> TTS).
  3. Whenever CallSession has a spoken reply ready, it's downsampled back to
     8 kHz mu-law, base64-framed, and sent back down the same websocket so
     Twilio plays it to the caller.
  4. On hang-up, CallSession.finish() logs the transcript + summary to Zoho CRM.

Run with: uvicorn telephony.twilio_stream:app --host 0.0.0.0 --port 8080
Point a Twilio phone number's "A call comes in" webhook at POST /voice on a
publicly reachable URL (e.g. via ngrok in development).
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from audio.codecs import mulaw_to_pcm16, pcm16_to_mulaw, resample_pcm16
from config import settings
from pipeline.orchestrator import SAMPLE_RATE, CallSession

logger = logging.getLogger("telephony.twilio_stream")

TWILIO_SAMPLE_RATE = 8000
OUTBOUND_FRAME_MS = 20
OUTBOUND_FRAME_BYTES = int(TWILIO_SAMPLE_RATE * (OUTBOUND_FRAME_MS / 1000)) * 2  # PCM16 bytes/frame before encoding

app = FastAPI(title="Goldentrade voice pipeline - Twilio bridge")


@app.post("/voice")
async def voice_webhook(request: Request) -> Response:
    form = await request.form()
    caller_phone = str(form.get("From", "unknown"))

    stream_url = settings.twilio.media_stream_url
    if not stream_url:
        base = str(request.base_url).replace("http://", "ws://").replace("https://", "wss://")
        stream_url = f"{base.rstrip('/')}/media"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}">
      <Parameter name="callerPhone" value="{caller_phone}" />
    </Stream>
  </Connect>
</Response>"""
    return Response(content=twiml, media_type="text/xml")


@app.websocket("/media")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()

    session: CallSession | None = None

    try:
        while True:
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            event = message.get("event")

            if event == "start":
                custom_params = message["start"].get("customParameters", {})
                caller_phone = custom_params.get("callerPhone", "unknown")
                session = CallSession(caller_phone=caller_phone)
                logger.info("Call started for %s", caller_phone)

            elif event == "media" and session is not None:
                stream_sid = message["streamSid"]
                mulaw_bytes = base64.b64decode(message["media"]["payload"])
                pcm16_8k = mulaw_to_pcm16(mulaw_bytes)
                pcm16_16k = resample_pcm16(pcm16_8k, TWILIO_SAMPLE_RATE, SAMPLE_RATE)

                reply_pcm16_16k = session.push_audio_16k(pcm16_16k)
                if reply_pcm16_16k:
                    await _send_audio(websocket, stream_sid, reply_pcm16_16k)

            elif event == "stop":
                logger.info("Call stopped")
                break

    except WebSocketDisconnect:
        pass
    finally:
        if session is not None:
            call_id = session.finish()
            logger.info("Logged call to Zoho CRM: %s", call_id)


async def _send_audio(websocket: WebSocket, stream_sid: str, pcm16_16k: bytes) -> None:
    pcm16_8k = resample_pcm16(pcm16_16k, SAMPLE_RATE, TWILIO_SAMPLE_RATE)
    mulaw_bytes = pcm16_to_mulaw(pcm16_8k)

    for offset in range(0, len(mulaw_bytes), OUTBOUND_FRAME_BYTES // 2):
        chunk = mulaw_bytes[offset : offset + OUTBOUND_FRAME_BYTES // 2]
        if not chunk:
            continue
        await websocket.send_text(
            json.dumps(
                {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": base64.b64encode(chunk).decode("ascii")},
                }
            )
        )
