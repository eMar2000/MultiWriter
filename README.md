# MultiWriter - Multi-Agent Novel Outline Generator

A scalable multi-agent AI system that generates comprehensive novel outlines with plot structure, characters, world-building, and scene beats.

## Architecture

This system uses specialized AI agents that collaborate like a writers' room:
- **Narrative Architect**: Story structure and plot beats
- **Theme & Premise**: Thematic coherence
- **Character Psychodynamics**: Character profiles and arcs
- **Worldbuilding**: World rules and consistency
- **Scene Dynamics**: Scene breakdowns

## Setup Status

- [x] Python virtual environment created (`venv/`)
- [x] Python dependencies installed
- [x] Configuration file ready (`config/config.yaml`)
- [ ] Ollama installed and running (see below)
- [ ] LLM model pulled

## Quick Start

### 1. Install Ollama (One-time setup)

Download and install Ollama for Windows from: https://ollama.com/download

After installation, Ollama runs automatically as a background service.

### 2. Pull the LLM Model (One-time setup)

Open a terminal and run:
```bash
ollama pull qwen2.5:14b
```

This downloads the Qwen 2.5 14B model (~9GB). Wait for the download to complete.

### 3. Run the CLI

Activate the virtual environment and run:
```powershell
.\venv\Scripts\Activate.ps1
python -m src.cli.main
```

Follow the interactive prompts to provide:
- Novel premise
- Genre
- Key elements
- Character concepts

The system will generate a complete outline saved as Markdown in the `output/` directory.

## Alternative Models

You can use different Ollama models by editing `config/config.yaml`:

| Model | Size | VRAM Required |
|-------|------|---------------|
| `qwen2.5:14b` (default) | ~9GB | ~10GB |
| `llama3.1:8b` | ~4.7GB | ~6GB |
| `mistral-nemo:12b` | ~7GB | ~8GB |
| `llama3.1:70b` | ~40GB | ~48GB |

## Optional: Vector Store (Qdrant)

For enhanced semantic search capabilities, you can run Qdrant via Docker:

```bash
docker-compose up -d qdrant
```

This is optional for basic usage.

## Development

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black src/ tests/
```

Type checking:
```bash
mypy src/
```

## License

Proprietary
