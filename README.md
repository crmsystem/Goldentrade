# Goldentrade - AI Voice Call Pipeline

An AI phone agent pipeline:

```
Customer Call
      |
      v
 Twilio / LiveKit          <- telephony transport, brings audio in/out
      |
      v
 Silero VAD                <- audio/vad.py, pipeline/orchestrator.py
      |
      v
 Whisper / Deepgram (STT)  <- stt/
      |
      v
 GPT / Claude (LLM)        <- llm/
      |
      v
 ElevenLabs / Piper (TTS)  <- tts/
      |
      v
 Zoho CRM                  <- crm/zoho_client.py (logs the call as an activity)
```

## Module map

| Stage | Module | Notes |
|---|---|---|
| Telephony | `telephony/twilio_stream.py` | FastAPI app: TwiML webhook + Media Streams websocket bridge |
| Codecs | `audio/codecs.py` | mu-law <-> PCM16, 8k <-> 16k resampling (no `audioop` dependency) |
| VAD | `audio/vad.py` | Silero VAD load/streaming helpers |
| STT | `stt/` | `whisper_stt.py` (local, `faster-whisper`), `deepgram_stt.py` (hosted REST) |
| LLM | `llm/` | `anthropic_llm.py` (Claude), `openai_llm.py` (GPT) |
| TTS | `tts/` | `elevenlabs_tts.py` (hosted REST, raw PCM output), `piper_tts.py` (local binary) |
| Orchestration | `pipeline/orchestrator.py` | `CallSession`: per-call VAD -> STT -> LLM -> TTS state machine |
| CRM | `crm/zoho_client.py` | OAuth2 self-client, phone lookup, creates a `Calls` record with transcript + summary |

Every provider stage (STT/LLM/TTS) is picked at runtime from `.env` (`STT_PROVIDER`,
`LLM_PROVIDER`, `TTS_PROVIDER`) behind a small `Protocol` in each package's `base.py`,
so swapping Whisper for Deepgram, or Claude for GPT, is a config change, not a code change.

## Is there a Zoho equivalent for Whisper/Deepgram (STT) or ElevenLabs/Piper (TTS)?

Short answer: **no direct equivalent** you can drop in as a generic STT/TTS API.
What Zoho actually offers in this space:

- **Zoho Voice** - Zoho's own cloud telephony/PBX product. It could replace Twilio for
  *placing and receiving* calls if you're already consolidating on Zoho, but it's a calling
  product, not an audio API you point arbitrary streams at.
- **Zia call transcription / Zia Voice** - Zoho's AI (Zia) can transcribe and summarize calls
  made *through Zoho Voice/Zoho Telephony* and attach that to CRM/Desk records automatically.
  It's the closest thing Zoho has to "STT + summarization," but it only operates on calls made
  inside Zoho's own telephony stack - it isn't exposed as an API you can feed a custom
  Twilio/LiveKit audio stream into, and there's no equivalent for arbitrary TTS synthesis.
- There is no published Zoho product comparable to ElevenLabs/Piper for text-to-speech.

Given that, this pipeline keeps Twilio/LiveKit + Whisper/Deepgram + ElevenLabs/Piper for the
real-time voice leg, and uses **Zoho CRM only as the system of record**: `crm/zoho_client.py`
looks the caller up by phone number (Contacts, then Leads) and logs a `Calls` activity with the
full transcript and an LLM-generated summary once the call ends. If you later migrate calling
infrastructure to Zoho Voice, the STT/LLM/TTS stages here are unaffected - only
`telephony/twilio_stream.py` would need a Zoho Voice-flavored counterpart.

## Setup

1. `pip install -r requirements-py314.txt`
2. `cp .env.example .env` and fill in credentials for whichever providers you're using.
3. Zoho: create a **Self Client** in the [Zoho API Console](https://api-console.zoho.com/) with
   scopes `ZohoCRM.modules.calls.CREATE,ZohoCRM.modules.leads.READ,ZohoCRM.modules.contacts.READ`,
   generate a refresh token, and set `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` / `ZOHO_REFRESH_TOKEN`.
4. Run the bridge: `uvicorn telephony.twilio_stream:app --host 0.0.0.0 --port 8080`
5. Point a Twilio number's "A call comes in" webhook (voice, HTTP POST) at
   `https://<your-host>/voice` (use `ngrok http 8080` for local development).

## LiveKit

`TELEPHONY_PROVIDER=livekit` is reserved in `config.py` for a LiveKit Agents-based bridge, which
would reuse `pipeline/orchestrator.py`'s `CallSession` exactly as `telephony/twilio_stream.py`
does today - only the audio transport (LiveKit room <-> PCM16) differs. Not yet implemented.

## Testing

### Automated tests (no credentials, no network)

```
pip install -r requirements-py314.txt
pytest tests/ -v
```

These cover the parts that don't require a live call, a model download, or a paid API key:

- `tests/test_codecs.py` - mu-law/PCM16 encode-decode correctness (checked against the stdlib
  `audioop` reference where available) and 8k<->16k resampling
- `tests/test_orchestrator.py` - `CallSession`'s VAD segmentation -> STT -> LLM -> TTS ->
  Zoho-logging control flow, using fake providers so no model weights or API keys are needed
- `tests/test_zoho_client.py` - OAuth token refresh, phone-based Contact/Lead lookup, and Call
  record construction, using monkeypatched HTTP responses instead of the real Zoho API

`tests/conftest.py` stubs `torch`/`soundfile` only if they aren't already installed, so these
tests stay fast on a lightweight box; anywhere the real packages are present (e.g. a full
`requirements-py314.txt` install), they're used as-is.

### Testing a single provider with real credentials

Each provider class can be exercised directly, in isolation, once its `.env` values are set:

```python
# STT
from stt.whisper_stt import WhisperSTT
WhisperSTT().transcribe_pcm16(open("sample_16k_mono.raw", "rb").read())

# LLM
from llm.anthropic_llm import ClaudeLLM
from llm.base import ConversationState
ClaudeLLM().reply(ConversationState(), "What are your hours?")

# TTS
from tts.elevenlabs_tts import ElevenLabsTTS
audio = ElevenLabsTTS().synthesize_pcm16("Hello, thanks for calling.")
open("out.pcm", "wb").write(audio)

# Zoho CRM
from crm.zoho_client import ZohoCRMClient
ZohoCRMClient().find_by_phone("+1 555 123 4567")
```

### End-to-end live call test

The full pipeline can only be verified against a real phone call, since Twilio Media Streams,
STT/TTS latency, and audio quality don't show up in unit tests:

1. Fill in real credentials in `.env` for whichever STT/LLM/TTS providers you picked.
2. `uvicorn telephony.twilio_stream:app --host 0.0.0.0 --port 8080`
3. In another terminal: `ngrok http 8080`, then set that number's Twilio "A call comes in"
   webhook to `https://<ngrok-id>.ngrok.io/voice` (HTTP POST).
4. Call the Twilio number from a real phone and talk to it. Watch the bridge's logs for
   `Call started for <phone>` and `Logged call to Zoho CRM: <id>` on hang-up.
5. In Zoho CRM, open the matched Contact/Lead (or search the `Calls` module directly) and
   confirm a new Call record appeared with the transcript and summary in its Description.

Things worth listening/checking for on that first live call: turn-taking latency (how long
after you stop talking before the agent replies), whether Silero VAD is cutting you off mid
-sentence or waiting too long after you finish, and whether the mu-law round trip through
`audio/codecs.py` introduces any audible artifacts compared to the TTS provider's raw output.
