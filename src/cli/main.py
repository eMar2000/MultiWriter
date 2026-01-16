"""CLI interface for MultiWriter"""

import asyncio
import yaml
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.models import NovelInput, Genre
from src.llm import OllamaClient
from src.memory import DynamoDBState, S3ObjectStore, QdrantVectorStore
from src.orchestrator import Orchestrator
from src.export import MarkdownExporter


console = Console()


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        console.print(f"[yellow]Warning: Config file not found at {config_path}[/yellow]")
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_llm_provider(config: dict) -> OllamaClient:
    """Create LLM provider from config"""
    llm_config = config.get("llm", {})
    return OllamaClient(
        model=llm_config.get("model", "llama3.1:70b"),
        base_url=llm_config.get("base_url", "http://localhost:11434"),
        timeout=llm_config.get("timeout", 300)
    )


def create_storage(config: dict):
    """Create storage instances from config"""
    storage_config = config.get("storage", {})

    # DynamoDB
    dynamodb_config = storage_config.get("dynamodb", {})
    structured_state = DynamoDBState(
        region=dynamodb_config.get("region", "us-east-1"),
        endpoint_url=dynamodb_config.get("endpoint_url"),
        table_prefix=""
    )

    # S3
    s3_config = storage_config.get("s3", {})
    object_store = S3ObjectStore(
        bucket=s3_config.get("bucket", "multiwriter-outlines"),
        region=s3_config.get("region", "us-east-1"),
        endpoint_url=s3_config.get("endpoint_url")
    )

    # Qdrant
    qdrant_config = storage_config.get("qdrant", {})
    vector_store = QdrantVectorStore(
        host=qdrant_config.get("host", "localhost"),
        port=qdrant_config.get("port", 6333),
        collection_name=qdrant_config.get("collection_name", "multiwriter-embeddings"),
        vector_size=qdrant_config.get("vector_size", 768)
    )

    return structured_state, object_store, vector_store


def collect_novel_input() -> NovelInput:
    """Collect novel input from user interactively"""
    console.print(Panel("[bold blue]MultiWriter - Novel Outline Generator[/bold blue]", border_style="blue"))
    console.print()

    # Premise
    premise = Prompt.ask("[bold]Enter the novel premise[/bold]", console=console)

    # Genre
    console.print("\n[bold]Available genres:[/bold]")
    genres = [g.value for g in Genre]
    for i, genre in enumerate(genres, 1):
        console.print(f"  {i}. {genre}")

    genre_choice = Prompt.ask(
        "\n[bold]Select genre (number or name)[/bold]",
        default="1",
        console=console
    )

    # Parse genre choice
    try:
        genre_idx = int(genre_choice) - 1
        if 0 <= genre_idx < len(genres):
            genre = Genre(genres[genre_idx])
        else:
            genre = Genre.OTHER
    except ValueError:
        # Try to match by name
        genre_lower = genre_choice.lower()
        try:
            genre = Genre(genre_lower)
        except ValueError:
            genre = Genre.OTHER

    # Target length
    target_length_str = Prompt.ask(
        "[bold]Target word count (optional)[/bold]",
        default="",
        console=console
    )
    target_length = int(target_length_str) if target_length_str else None

    # Key elements
    console.print("\n[bold]Key story elements (press Enter after each, empty line to finish):[/bold]")
    key_elements = []
    while True:
        element = Prompt.ask("  Element", default="", console=console)
        if not element:
            break
        key_elements.append(element)

    # Character concepts
    console.print("\n[bold]Character concepts (press Enter after each, empty line to finish):[/bold]")
    character_concepts = []
    while True:
        concept = Prompt.ask("  Concept", default="", console=console)
        if not concept:
            break
        character_concepts.append(concept)

    # Desired theme
    desired_theme = Prompt.ask(
        "[bold]Desired theme (optional)[/bold]",
        default="",
        console=console
    )
    desired_theme = desired_theme if desired_theme else None

    return NovelInput(
        premise=premise,
        genre=genre,
        target_length=target_length,
        key_elements=key_elements,
        character_concepts=character_concepts,
        desired_theme=desired_theme
    )


async def generate_outline(novel_input: NovelInput, config: dict) -> Optional[dict]:
    """Generate novel outline"""
    # Create components
    llm_provider = create_llm_provider(config)
    structured_state, object_store, vector_store = create_storage(config)

    # Create orchestrator
    orchestrator = Orchestrator(
        llm_provider=llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        config=config
    )

    # Generate outline with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating outline...", total=None)

        try:
            outline = await orchestrator.generate_outline(novel_input)
            progress.update(task, description="Outline generated successfully!")
            return outline
        except Exception as e:
            console.print(f"[red]Error generating outline: {str(e)}[/red]")
            return None
        finally:
            # Close LLM provider session
            await llm_provider.close()


@click.command()
@click.option(
    "--premise",
    type=str,
    help="Novel premise (if not provided, will be prompted)"
)
@click.option(
    "--genre",
    type=click.Choice([g.value for g in Genre], case_sensitive=False),
    help="Novel genre"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("output"),
    help="Output directory for generated outline"
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file"
)
def main(premise: Optional[str], genre: Optional[str], output: Path, config: Optional[Path]):
    """MultiWriter - Multi-Agent Novel Outline Generator"""

    # Load config
    if config:
        with open(config, "r", encoding="utf-8") as f:
            app_config = yaml.safe_load(f)
    else:
        app_config = load_config()

    # Collect novel input
    if premise:
        # Use provided premise
        genre_enum = Genre(genre) if genre else Genre.OTHER
        novel_input = NovelInput(
            premise=premise,
            genre=genre_enum
        )
    else:
        # Collect interactively
        novel_input = collect_novel_input()

    # Display summary
    console.print()
    console.print(Panel(
        f"[bold]Premise:[/bold] {novel_input.premise}\n"
        f"[bold]Genre:[/bold] {novel_input.genre.value}",
        title="Novel Summary",
        border_style="green"
    ))
    console.print()

    # Confirm
    if not Confirm.ask("Generate outline with these parameters?", console=console):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Generate outline
    outline = asyncio.run(generate_outline(novel_input, app_config))

    if not outline:
        console.print("[red]Failed to generate outline[/red]")
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

    table.add_row("Theme", "✓" if outline.theme else "✗")
    table.add_row("Plot Structure", "✓" if outline.plot_structure else "✗")
    table.add_row(f"Characters ({len(outline.characters) if outline.characters else 0})", "✓" if outline.characters else "✗")
    table.add_row("World Rules", "✓" if outline.world_rules else "✗")
    table.add_row(f"Scenes ({len(outline.scenes) if outline.scenes else 0})", "✓" if outline.scenes else "✗")

    console.print()
    console.print(table)


if __name__ == "__main__":
    main()
