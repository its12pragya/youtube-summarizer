"""YouTube video summarizer — CLI entry point."""
import json
import os
import sys

import click
from dotenv import load_dotenv
from google import genai
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from utils import extract_video_id, fetch_transcript, truncate_transcript

load_dotenv()
console = Console()


def summarize(transcript: str) -> dict:
    """Send transcript to Gemini and parse the JSON response."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=USER_PROMPT_TEMPLATE.format(transcript=transcript),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    return json.loads(response.text)


def render(summary: dict, truncated: bool) -> None:
    """Pretty-print the summary to the terminal."""
    if truncated:
        console.print("[yellow]Note: transcript was long and has been truncated.[/yellow]\n")

    console.print(Panel(summary["tldr"], title="TL;DR", border_style="cyan"))
    console.print()

    console.print(Rule("Key Takeaways"))
    for i, item in enumerate(summary["key_takeaways"], 1):
        console.print(f"\n[bold cyan]{i}. [{item['timestamp']}][/bold cyan] {item['point']}")
        console.print(f"   [dim]{item['why_it_matters']}[/dim]")

    if summary.get("notable_quotes"):
        console.print("\n")
        console.print(Rule("Notable Quotes"))
        for q in summary["notable_quotes"]:
            console.print(f'\n[italic]"{q["quote"]}"[/italic] [dim]— {q["timestamp"]}[/dim]')

    console.print("\n")
    console.print(Rule("Who Should Watch"))
    console.print(f"[green]Watch if:[/green] {summary['target_audience']}")
    console.print(f"[red]Skip if:[/red]  {summary['skip_if']}")


@click.command()
@click.argument("url")
@click.option("--lang", default="en", help="Preferred transcript language (default: en)")
@click.option("--save", is_flag=True, help="Also save output as markdown")
def main(url: str, lang: str, save: bool) -> None:
    """Summarize a YouTube video from its URL."""
    try:
        with console.status("[cyan]Extracting video ID..."):
            video_id = extract_video_id(url)

        with console.status("[cyan]Fetching transcript..."):
            transcript = fetch_transcript(video_id, lang=lang)
            transcript, truncated = truncate_transcript(transcript)

        with console.status("[cyan]Summarizing with Gemini..."):
            summary = summarize(transcript)

        console.print()
        render(summary, truncated)

        if save:
            filename = f"summary_{video_id}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# Summary: {url}\n\n")
                f.write(f"**TL;DR:** {summary['tldr']}\n\n")
                f.write("## Key Takeaways\n\n")
                for item in summary["key_takeaways"]:
                    link = f"https://youtube.com/watch?v={video_id}&t={item['timestamp']}"
                    f.write(f"- **[{item['timestamp']}]({link})** — {item['point']}\n")
                    f.write(f"  - _{item['why_it_matters']}_\n")
            console.print(f"\n[green]Saved to {filename}[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()