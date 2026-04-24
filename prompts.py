"""Prompt templates for the YouTube summarizer."""

SYSTEM_PROMPT = """You are an expert at distilling long-form video content like podcasts into useful, scannable summaries. You never invent facts that aren't in the transcript. When citing moments, always include the timestamp from the transcript."""

USER_PROMPT_TEMPLATE = """Summarize this YouTube transcript. Return ONLY valid JSON matching this exact schema:

{{
  "Guests": ["Name of Interviewer", "Name of Interviewee(s) if applicable"],
  "tldr": "5-6 sentence summary of the whole video",
  "key_takeaways": [
    {{"timestamp": "MM:SS", "point": "the main idea", "why_it_matters": "why a viewer should care"}}
  ],
  "notable_quotes": [
    {{"timestamp": "MM:SS", "quote": "the exact or near-exact quote"}}
  ],
  "target_audience": "who benefits most from watching this",
  "skip_if": "who should skip this video"
}}

Rules:
- Aim for 5-7 key_takeaways
- Include 2-3 notable_quotes only if genuinely memorable; empty array if none stand out
- Timestamps must come from the transcript for each takeaway, formatted as MM:SS or HH:MM:SS
- Give the exact timestamp of the takeaway from the transcript, not an approximation
- Don't make up quotes; only include if clearly stated in the transcript with a timestamp


Transcript:
{transcript}
"""