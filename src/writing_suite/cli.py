"""CLI entrypoint.

Usage:
    hermes-writer run --brief brief.md --output essay.docx [--style-sample s1.txt -s s2.txt]
    hermes-writer health
    hermes-writer estimate --brief brief.md
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .config import Settings
from .mimo_client import ChatMessage, MimoClient
from .pipeline import PipelineInput, WritingPipeline


console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Hermes-MiMo Writer — multi-agent academic writing pipeline."""
    ctx.ensure_object(dict)
    _setup_logging(verbose)


@cli.command()
@click.option("--brief", required=True, type=click.Path(exists=True, dir_okay=False), help="Path to brief / rubric file.")
@click.option("--output", required=True, type=click.Path(dir_okay=False), help="Output .docx path.")
@click.option("-s", "--style-sample", "style_samples", multiple=True, type=click.Path(exists=True, dir_okay=False), help="Style sample text file (repeatable).")
@click.option("--skip-sanitize", is_flag=True, help="Skip the AI-detector sanitizer pass (faster, lower quality).")
def run(brief: str, output: str, style_samples: tuple[str, ...], skip_sanitize: bool) -> None:
    """Generate a DOCX from a brief."""
    settings = Settings.from_env()
    settings.ensure_output_dir()

    brief_text = Path(brief).read_text(encoding="utf-8")
    samples = [Path(p).read_text(encoding="utf-8") for p in style_samples]

    pipeline = WritingPipeline(settings)
    pi = PipelineInput(
        brief_text=brief_text,
        style_samples=samples,
        output_path=Path(output),
        skip_sanitize=skip_sanitize,
    )

    result = asyncio.run(pipeline.run(pi))

    table = Table(title="Pipeline Token Ledger", show_lines=False)
    table.add_column("Agent", style="cyan")
    table.add_column("Tokens", justify="right", style="green")
    for agent, tokens in sorted(result.ledger.by_agent.items()):
        table.add_row(agent, f"{tokens:,}")
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{result.ledger.total:,}[/bold]")
    console.print(table)
    console.print(f"\n[bold green]Output:[/] {result.output_path}")
    console.print(f"[bold]Words:[/] {result.sanitized.total_words}")


@cli.command()
def health() -> None:
    """Verify the MiMo Token Plan endpoint is reachable with the configured key."""
    async def _check() -> None:
        settings = Settings.from_env()
        async with MimoClient(settings) as client:
            try:
                result = await client.chat(
                    [
                        ChatMessage(role="system", content="reply with the single word: ok"),
                        ChatMessage(role="user", content="ping"),
                    ],
                    temperature=0,
                    max_tokens=8,
                    lite=True,
                )
            except Exception as e:
                console.print(f"[bold red]FAILED[/]: {e}")
                sys.exit(1)
            console.print(f"[bold green]OK[/] — model={settings.mimo_model_lite} tokens={result.token_total}")

    asyncio.run(_check())


@cli.command()
@click.option("--brief", required=True, type=click.Path(exists=True, dir_okay=False))
def estimate(brief: str) -> None:
    """Estimate token cost for a brief without running the full pipeline."""
    text = Path(brief).read_text(encoding="utf-8")
    word_count = _detect_target_words(text)
    # Heuristic: 1 word output ≈ 1.4 tokens; pipeline overhead ≈ 4x
    base = int(word_count * 1.4)
    estimate_tokens = base * 4
    console.print(
        f"Target words: [cyan]{word_count}[/]\n"
        f"Estimated total tokens: [green]{estimate_tokens:,}[/] "
        f"(parser+style+outline+drafter+sanitizer+citations)\n"
        f"At MiMo Pro overseas pricing (~$1.50/M effective): [bold]~${estimate_tokens / 1_000_000 * 1.5:.4f}[/]"
    )


def _detect_target_words(text: str) -> int:
    import re

    for pattern in [
        r"(\d{3,5})\s*(?:kata|words|word)",
        r"minimum\s*(\d{3,5})",
        r"at least\s*(\d{3,5})",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 1000


if __name__ == "__main__":
    cli()
