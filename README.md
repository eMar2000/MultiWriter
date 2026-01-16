# MultiWriter - Multi-Agent Novel Outline Generator

A scalable multi-agent AI system that generates comprehensive novel outlines with plot structure, characters, world-building, and scene beats.

## Architecture

This system uses specialized AI agents that collaborate like a writers' room:
- **Narrative Architect**: Story structure and plot beats
- **Theme & Premise**: Thematic coherence
- **Character Psychodynamics**: Character profiles and arcs
- **Worldbuilding**: World rules and consistency
- **Scene Dynamics**: Scene breakdowns

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- AWS account (for DynamoDB and S3) - optional for local development

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start services (Qdrant and Ollama):
```bash
docker-compose up -d
```

4. Pull the Llama 3.1 70B model:
```bash
docker exec -it multiwriter-ollama ollama pull llama3.1:70b
```

### Configuration

Copy `config/config.yaml.example` to `config/config.yaml` and configure:
- LLM settings
- AWS credentials (if using DynamoDB/S3)
- Qdrant connection settings

## Usage

Run the CLI to generate a novel outline:

```bash
python -m src.cli.main
```

Follow the interactive prompts to provide:
- Novel premise
- Genre
- Key elements
- Character concepts

The system will generate a complete outline saved as Markdown.

## Development

Run tests:
```bash
pytest tests/
```

## License

Proprietary
