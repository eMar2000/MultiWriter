"""CLI interface for MultiWriter - Document-Driven Outline Generator"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.models import NovelInput, Genre
from src.llm import OllamaClient
from src.memory import LocalFileState, LocalObjectStore, QdrantVectorStore
from src.orchestrator import DocumentOrchestrator
from src.export import MarkdownExporter


console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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

    # Check storage provider (default to local)
    provider = storage_config.get("provider", "local")

    if provider == "local":
        # Local file-based storage
        local_config = storage_config.get("local", {})
        structured_state = LocalFileState(
            storage_dir=local_config.get("data_dir", "./data")
        )
        object_store = LocalObjectStore(
            storage_dir=local_config.get("objects_dir", "./data/objects")
        )
    else:
        # AWS storage (DynamoDB + S3) - requires credentials
        from src.memory import DynamoDBState, S3ObjectStore

        dynamodb_config = storage_config.get("dynamodb", {})
        structured_state = DynamoDBState(
            region=dynamodb_config.get("region", "us-east-1"),
            endpoint_url=dynamodb_config.get("endpoint_url"),
            table_prefix=""
        )

        s3_config = storage_config.get("s3", {})
        object_store = S3ObjectStore(
            bucket=s3_config.get("bucket", "multiwriter-outlines"),
            region=s3_config.get("region", "us-east-1"),
            endpoint_url=s3_config.get("endpoint_url")
        )

    # Qdrant (optional - gracefully handle if not available)
    vector_store = None
    qdrant_config = storage_config.get("qdrant", {})
    if qdrant_config.get("enabled", False):
        try:
            vector_store = QdrantVectorStore(
                host=qdrant_config.get("host", "localhost"),
                port=qdrant_config.get("port", 6333),
                collection_name=qdrant_config.get("collection_name", "multiwriter-embeddings"),
                vector_size=qdrant_config.get("vector_size", 768)
            )
        except Exception:
            # Qdrant not available, continue without vector store
            pass

    return structured_state, object_store, vector_store


async def generate_from_documents(
    worldbuilding: Path,
    characters: Path,
    scenes: Path,
    output: Path,
    config: dict
) -> Optional[dict]:
    """Generate outline from document inputs"""
    # Build novel input (minimal - documents contain the info)
    novel_input = NovelInput(
        premise="Generated from documents",
        genre=Genre.OTHER
    )

    # Create components
    llm_provider = create_llm_provider(config)
    structured_state, object_store, vector_store = create_storage(config)

    orchestrator = DocumentOrchestrator(
        llm_provider=llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        config=config
    )

    try:
        outline = await orchestrator.process_documents(
            worldbuilding_path=worldbuilding,
            characters_path=characters,
            scenes_path=scenes,
            novel_input=novel_input
        )
        return outline
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return None
    finally:
        await llm_provider.close()


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
