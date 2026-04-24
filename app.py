"""Streamlit web UI for the YouTube summarizer."""
import json
import os
import time
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    HRFlowable,
)

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from utils import extract_video_id, fetch_transcript, truncate_transcript

load_dotenv()

# ---------- Page config ----------
st.set_page_config(
    page_title="YouTube Summarizer",
    page_icon="🎥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- Custom CSS ----------
st.markdown(
    """
    <style>
    /* Hide Streamlit's default chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Global font smoothing */
    html, body, [class*="css"] {
        -webkit-font-smoothing: antialiased;
    }

    /* Hero section */
    .hero {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .hero h1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #000000;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    .hero p {
        color: #52525B;
        font-size: 1.05rem;
        max-width: 520px;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* Provider pill buttons */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"],
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        border-radius: 999px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    /* URL input — white background, black border */
    .stTextInput > div > div > input {
        border-radius: 10px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        border: 1.5px solid #000000;
        background-color: #FFFFFF;
        color: #111111;
    }
    .stTextInput > div > div > input::placeholder {
        color: #9CA3AF;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4F46E5;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    }

    /* Primary button (Summarize) */
    .stButton > button[kind="primary"] {
        border-radius: 10px;
        font-weight: 500;
        padding: 0.6rem 2rem;
        background-color: #4F46E5;
        border: none;
        color: #FFFFFF;
        transition: background-color 0.15s ease, transform 0.1s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #4338CA;
        transform: translateY(-1px);
    }

    /* TL;DR card */
    .tldr-card {
        background-color: rgba(99, 102, 241, 0.06);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        font-size: 1.02rem;
        line-height: 1.65;
        color: #1F2937;
    }
    .tldr-card b {
        color: #4F46E5;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 500;
        border-radius: 8px;
    }

    /* Quote styling */
    .quote-card {
        border-left: 3px solid #4F46E5;
        padding: 0.75rem 1.25rem;
        margin: 0.75rem 0;
        background-color: rgba(79, 70, 229, 0.03);
        font-style: italic;
        border-radius: 0 8px 8px 0;
        color: #374151;
        line-height: 1.6;
    }
    .quote-ts {
        display: block;
        font-style: normal;
        color: #6B7280;
        font-size: 0.82rem;
        margin-top: 0.5rem;
    }

    /* Audience cards */
    .audience-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin: 1.25rem 0;
    }
    .audience-card {
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        line-height: 1.55;
    }
    .audience-watch {
        background-color: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #1F2937;
    }
    .audience-skip {
        background-color: rgba(244, 114, 182, 0.06);
        border: 1px solid rgba(244, 114, 182, 0.3);
        color: #1F2937;
    }
    .audience-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }

    /* Section headers */
    h3 {
        color: #111111 !important;
        font-weight: 600 !important;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #6B7280;
        font-size: 0.85rem;
        padding: 2rem 0 1rem 0;
    }
    .footer a {
        color: #4F46E5;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Session state for provider ----------
if "provider" not in st.session_state:
    st.session_state.provider = "Groq"

# ---------- Hero ----------
st.markdown(
    """
    <div class="hero">
        <h1>🎥 YouTube Summarizer</h1>
        <p>Paste any YouTube URL and get a structured summary with timestamps, 
        key takeaways, and memorable quotes — in seconds.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Provider picker (main page, pill buttons) ----------
st.markdown(
    "<p style='text-align:center; color:#6B7280; margin-bottom:0.5rem; font-size:0.85rem;'>Choose your AI engine</p>",
    unsafe_allow_html=True,
)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        if st.button(
            "⚡ Groq (fast)",
            use_container_width=True,
            type="primary" if st.session_state.provider == "Groq" else "secondary",
        ):
            st.session_state.provider = "Groq"
            st.rerun()
    with p_col2:
        if st.button(
            "✨ Gemini",
            use_container_width=True,
            type="primary" if st.session_state.provider == "Gemini" else "secondary",
        ):
            st.session_state.provider = "Gemini"
            st.rerun()

provider = st.session_state.provider

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

# ---------- URL input ----------
url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed",
)

# ---------- Summarize button ----------
btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
with btn_col2:
    summarize_clicked = st.button(
        "Summarize →",
        type="primary",
        use_container_width=True,
        disabled=not url,
    )


# ---------- PDF generator ----------
def build_pdf(summary: dict, video_url: str, video_id: str) -> bytes:
    """Generate a clean PDF from the summary dict. Returns bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=HexColor("#4F46E5"),
        spaceAfter=8,
        alignment=TA_LEFT,
    )
    h2_style = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HexColor("#222222"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        textColor=HexColor("#333333"),
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=HexColor("#888888"),
        spaceAfter=4,
    )
    quote_style = ParagraphStyle(
        "Quote",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        textColor=HexColor("#444444"),
        leftIndent=14,
        spaceAfter=8,
        fontName="Helvetica-Oblique",
    )

    # Title + URL
    story.append(Paragraph("YouTube Video Summary", title_style))
    story.append(Paragraph(f'<a href="{video_url}" color="#4F46E5">{video_url}</a>', meta_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#DDDDDD")))

    # TL;DR
    story.append(Paragraph("TL;DR", h2_style))
    story.append(Paragraph(summary["tldr"], body_style))

    # Key takeaways
    story.append(Paragraph("Key Takeaways", h2_style))
    for i, item in enumerate(summary["key_takeaways"], 1):
        ts = item["timestamp"]
        jump_link = f"https://youtube.com/watch?v={video_id}&t={ts}"
        heading = (
            f'<b>{i}. [<a href="{jump_link}" color="#4F46E5">{ts}</a>]</b> '
            f'{item["point"]}'
        )
        story.append(Paragraph(heading, body_style))
        story.append(Paragraph(f'<i>{item["why_it_matters"]}</i>', meta_style))
        story.append(Spacer(1, 0.08 * inch))

    # Quotes
    if summary.get("notable_quotes"):
        story.append(Paragraph("Notable Quotes", h2_style))
        for q in summary["notable_quotes"]:
            story.append(Paragraph(f'"{q["quote"]}"', quote_style))
            story.append(Paragraph(f'— {q["timestamp"]}', meta_style))

    # Audience
    story.append(Paragraph("Who Should Watch", h2_style))
    story.append(Paragraph(f'<b>Watch if:</b> {summary["target_audience"]}', body_style))
    story.append(Paragraph(f'<b>Skip if:</b> {summary["skip_if"]}', body_style))

    # Footer
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#DDDDDD")))
    story.append(
        Paragraph(
            "Generated by YouTube Summarizer · Powered by Groq & Gemini",
            meta_style,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ---------- Main flow ----------
if summarize_clicked:
    try:
        with st.spinner("Extracting video ID..."):
            video_id = extract_video_id(url)

        with st.spinner("Fetching transcript..."):
            transcript = fetch_transcript(video_id)
            transcript, truncated = truncate_transcript(transcript)

        with st.spinner(f"Summarizing with {provider}..."):
            max_retries = 3
            summary = None

            for attempt in range(max_retries):
                try:
                    if provider == "Groq":
                        groq_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
                        if not groq_key:
                            st.error(
                                "Groq API key not found. Set GROQ_API_KEY in .env "
                                "or Streamlit secrets."
                            )
                            st.stop()
                        client = Groq(api_key=groq_key)
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {
                                    "role": "user",
                                    "content": USER_PROMPT_TEMPLATE.format(transcript=transcript),
                                },
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.3,
                        )
                        summary = json.loads(response.choices[0].message.content)
                    else:  # Gemini
                        gemini_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
                        if not gemini_key:
                            st.error(
                                "Gemini API key not found. Set GEMINI_API_KEY in .env "
                                "or Streamlit secrets."
                            )
                            st.stop()
                        client = genai.Client(api_key=gemini_key)
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=USER_PROMPT_TEMPLATE.format(transcript=transcript),
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                response_mime_type="application/json",
                                temperature=0.3,
                            ),
                        )
                        summary = json.loads(response.text)
                    break
                except Exception as e:
                    error_str = str(e)
                    is_retryable = (
                        "503" in error_str
                        or "429" in error_str
                        or "UNAVAILABLE" in error_str
                    )
                    if is_retryable and attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        st.info(
                            f"Provider is busy. Retrying in {wait_time}s... "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        raise

        # Truncation notice
        if truncated:
            st.warning(
                f"⚠️ Transcript was long. Summarizing the first {len(transcript):,} characters."
            )

        # TL;DR
        st.markdown(
            f'<div class="tldr-card"><b>TL;DR</b><br><br>{summary["tldr"]}</div>',
            unsafe_allow_html=True,
        )

        # Key takeaways
        st.markdown("### Key Takeaways")
        for i, item in enumerate(summary["key_takeaways"], 1):
            ts = item["timestamp"]
            link = f"https://youtube.com/watch?v={video_id}&t={ts}"
            with st.expander(f"**{i}.  [{ts}]  {item['point']}**"):
                st.write(item["why_it_matters"])
                st.markdown(f"[Jump to this moment in the video]({link})")

        # Quotes
        if summary.get("notable_quotes"):
            st.markdown("### Notable Quotes")
            for q in summary["notable_quotes"]:
                st.markdown(
                    f'<div class="quote-card">"{q["quote"]}"'
                    f'<span class="quote-ts">— {q["timestamp"]}</span></div>',
                    unsafe_allow_html=True,
                )

        # Audience
        st.markdown(
            f"""
            <div class="audience-row">
                <div class="audience-card audience-watch">
                    <div class="audience-label" style="color:#059669;">Watch if</div>
                    <div>{summary["target_audience"]}</div>
                </div>
                <div class="audience-card audience-skip">
                    <div class="audience-label" style="color:#DB2777;">Skip if</div>
                    <div>{summary["skip_if"]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Downloads
        st.markdown("### Download Summary")

        # Markdown content
        md_content = f"# Summary: {url}\n\n**TL;DR:** {summary['tldr']}\n\n## Key Takeaways\n\n"
        for item in summary["key_takeaways"]:
            link = f"https://youtube.com/watch?v={video_id}&t={item['timestamp']}"
            md_content += f"- **[{item['timestamp']}]({link})** — {item['point']}\n"
            md_content += f"  - _{item['why_it_matters']}_\n"

        # PDF bytes
        pdf_bytes = build_pdf(summary, url, video_id)

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                "Download as PDF",
                data=pdf_bytes,
                file_name=f"summary_{video_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with dl_col2:
            st.download_button(
                "Download as Markdown",
                data=md_content,
                file_name=f"summary_{video_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")

# ---------- Footer ----------
st.markdown(
    """
    <div class="footer">
        Built with Groq & Gemini · 
        <a href="https://github.com/your-username/youtube-summarizer">GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)