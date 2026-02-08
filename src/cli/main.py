"""CLI interface for MultiWriter - Document-Driven Outline Generator"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.models import NovelInput, Genre
from src.export import MarkdownExporter
from src.api import run_planning


console = Console()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for development troubleshooting
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from config.yaml"""
    try:
        import yaml
    except ImportError:
        console.print("[yellow]Warning: PyYAML not installed. Install with: pip install pyyaml[/yellow]")
        return {}

    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        console.print(f"[yellow]Warning: Config file not found at {config_path}[/yellow]")
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def generate_from_documents(
    worldbuilding: Path,
    characters: Path,
    scenes: Path,
    output: Path,
    config: dict
) -> Optional[dict]:
    """Generate outline from document inputs (delegates to run_planning)."""
    try:
        outline = await run_planning(
            worldbuilding_path=worldbuilding,
            characters_path=characters,
            scenes_path=scenes,
            novel_input=NovelInput(premise="Generated from documents", genre=Genre.OTHER),
            config=config
        )
        return outline
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return None


@click.command()
@click.option(
    '--worldbuilding',
    type=click.Path(exists=True, path_type=Path),
    default=Path("input/worldbuilding.md"),
    help="Path to worldbuilding markdown file (default: input/worldbuilding.md)"
)
@click.option(
    '--characters',
    type=click.Path(exists=True, path_type=Path),
    default=Path("input/characters.md"),
    help="Path to characters markdown file (default: input/characters.md)"
)
@click.option(
    '--scenes',
    type=click.Path(exists=True, path_type=Path),
    default=Path("input/scenes.md"),
    help="Path to scenes markdown file (default: input/scenes.md)"
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    default=Path("output"),
    help="Output directory for generated outline (default: output/)"
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file (default: config/config.yaml)"
)
def main(
    worldbuilding: Path,
    characters: Path,
    scenes: Path,
    output: Path,
    config: Optional[Path]
):
    """MultiWriter - Document-Driven Novel Outline Generator

    Generates a novel outline from three markdown input documents:
    - worldbuilding.md: World rules, locations, magic systems, etc.
    - characters.md: Character profiles, relationships, arcs
    - scenes.md: Scene concepts, plot points, key moments

    Example:
        python -m src.cli.main
    """
    # Load config
    if config:
        with open(config, "r", encoding="utf-8") as f:
            app_config = yaml.safe_load(f)
    else:
        app_config = load_config()

    # Verify input files exist (orchestrator will do detailed validation, but check basic existence here)
    if not worldbuilding.exists():
        console.print(f"[red]Error: Worldbuilding file not found: {worldbuilding}[/red]")
        console.print(f"[yellow]Expected location: {worldbuilding.absolute()}[/yellow]")
        logger.error(f"Worldbuilding file not found: {worldbuilding}")
        return

    if not characters.exists():
        console.print(f"[red]Error: Characters file not found: {characters}[/red]")
        console.print(f"[yellow]Expected location: {characters.absolute()}[/yellow]")
        logger.error(f"Characters file not found: {characters}")
        return

    if not scenes.exists():
        console.print(f"[red]Error: Scenes file not found: {scenes}[/red]")
        console.print(f"[yellow]Expected location: {scenes.absolute()}[/yellow]")
        logger.error(f"Scenes file not found: {scenes}")
        return

    # Display input summary
    console.print()
    console.print(Panel(
        "[bold blue]MultiWriter - Document-Driven Outline Generator[/bold blue]",
        border_style="blue"
    ))
    console.print()

    console.print(Panel(
        f"Worldbuilding: {worldbuilding}\n"
        f"Characters: {characters}\n"
        f"Scenes: {scenes}",
        title="Input Documents",
        border_style="cyan"
    ))
    console.print()

    # Generate outline
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating outline...", total=None)

        outline = asyncio.run(generate_from_documents(
            worldbuilding=worldbuilding,
            characters=characters,
            scenes=scenes,
            output=output,
            config=app_config
        ))

        progress.update(task, description="Complete!")

    if not outline:
        console.print("[red]Failed to generate outline[/red]")
        logger.error("Failed to generate outline")
        return

    # Export to Markdown
    exporter = MarkdownExporter()
    output.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    output_filename = f"outline_{outline.id}.md"
    output_path = output / output_filename

    exporter.export_to_file(outline, output_path)

    console.print()
    console.print(Panel(
        f"[bold green]Outline generated successfully![/bold green]\n\n"
        f"Saved to: [cyan]{output_path}[/cyan]\n\n"
        f"Outline ID: [dim]{outline.id}[/dim]",
        title="Success",
        border_style="green"
    ))

    # Display summary table
    table = Table(title="Outline Summary")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row(
        "Entity Registry",
        f"✓ {len(outline.entity_registry.entities) if outline.entity_registry else 0} entities"
    )
    table.add_row("Scenes", f"✓ {len(outline.scenes)}" if outline.scenes else "✗")
    table.add_row(
        "Arcs",
        f"✓ {len(outline.relationships.get('arcs', []))}" if outline.relationships.get('arcs') else "✗"
    )

    console.print()
    console.print(table)


if __name__ == "__main__":
    main()
