# 🎥 YouTube Summarizer

Paste any YouTube URL, get a structured summary in seconds — TL;DR, key takeaways with clickable timestamps, memorable quotes, and a "who should watch this" verdict. Export as PDF or Markdown.

The app can be used at - https://youtube-summarizer-ef5nf8fa4r6cjrkk9xk5j4.streamlit.app/


---

## Why I built this

I watch a lot of long-form content — podcasts, lectures, conference talks — and I wanted a tool that does more than paste a generic summary. I wanted timestamps I can jump to, the parts worth revisiting called out, and an honest take on who the video is actually for. So I built one.

## What it does

- **Structured summaries** — not a paragraph, a usable breakdown: TL;DR, 5–7 key takeaways with timestamps, notable quotes, and a watch/skip verdict
- **Clickable timestamps** — every takeaway links straight to that moment in the video
- **Multi-provider** — switch between Groq (fast, open-source Llama 3.3 70B) and Google Gemini 2.5 Flash with one click
- **Export** — download the summary as a styled PDF or Markdown with preserved timestamp links
- **Handles long videos** — smart truncation keeps requests under provider rate limits, with clear user feedback when it happens

## How it works

YouTube URL
↓
Extract video ID (regex, handles watch/shorts/youtu.be formats)
↓
Fetch transcript (youtube-transcript-api, with timestamps)
↓
Format + truncate to stay under token limits
↓
Send to LLM with structured JSON prompt (Groq or Gemini)
↓
Parse JSON → render in Streamlit → offer PDF/MD download

The whole pipeline is ~300 lines of Python across three files (`app.py`, `utils.py`, `prompts.py`).

## What I learned building this

A few things that weren't obvious going in:

- **Different LLM SDKs return different response shapes.** Groq follows OpenAI's format (`response.choices[0].message.content`), Gemini uses `response.text`. Abstracting over providers sounds trivial until you're actually doing it — it's why frameworks like LangChain exist.
- **Free-tier rate limits shape your architecture.** Groq's 12,000 tokens-per-minute cap on `llama-3.3-70b-versatile` meant long transcripts kept failing. The fix was tighter truncation (~25,000 chars) and exponential-backoff retry logic for transient 429/503 errors — patterns you'd build into any production LLM app.
- **Forcing JSON output is the difference between "demo" and "reliable".** Using `response_format={"type": "json_object"}` (Groq) and `response_mime_type="application/json"` (Gemini) eliminated a whole class of parsing failures I was hitting early on.
- **UX details matter more than I expected.** Showing users how many characters got truncated, letting them pick between providers, adding a focus ring on the input — none of it is hard, but together they're what makes the app feel built instead of thrown together.

## Tech stack

- **Frontend:** Streamlit with custom CSS
- **LLMs:** Groq (Llama 3.3 70B) · Google Gemini 2.5 Flash
- **Transcript:** youtube-transcript-api
- **PDF generation:** ReportLab
- **Deployment:** Streamlit Community Cloud

## Run it locally

Prerequisites: Python 3.10+, a free [Groq API key](https://console.groq.com/) and/or [Gemini API key](https://aistudio.google.com/).

```bash
git clone https://github.com/its12pragya/youtube-summarizer.git
cd youtube-summarizer

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Add your API keys
cp .env.example .env
# Open .env and paste your GROQ_API_KEY and/or GEMINI_API_KEY

streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Roadmap

- [ ] Map-reduce summarization for videos over 45 minutes
- [ ] Summary style presets (executive / student / ELI5)
- [ ] Batch mode for entire YouTube playlists
- [ ] Language support beyond English



