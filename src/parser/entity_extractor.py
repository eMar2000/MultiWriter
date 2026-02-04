"""Entity extraction from parsed documents"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from .document_parser import DocumentParser, ParsedSection
from src.models import EntitySummary, EntityType, EntityRegistry


class EntityExtractor:
    """Extract entities from parsed documents"""

    # Mapping of section titles/keywords to entity types
    TYPE_KEYWORDS = {
        EntityType.CHARACTER: ['character', 'protagonist', 'antagonist', 'hero', 'villain', 'person', 'cast'],
        EntityType.LOCATION: ['location', 'place', 'setting', 'world', 'city', 'kingdom', 'realm'],
        EntityType.ORGANIZATION: ['organization', 'faction', 'group', 'guild', 'company', 'clan'],
        EntityType.ITEM: ['item', 'artifact', 'weapon', 'object', 'macguffin'],
        EntityType.EVENT: ['event', 'history', 'backstory', 'incident'],
        EntityType.RULE: ['rule', 'magic', 'system', 'law', 'constraint', 'technology'],
        EntityType.SCENE_CONCEPT: ['scene', 'moment', 'beat', 'sequence', 'chapter', 'climax'],
    }

    def __init__(self):
        self.parser = DocumentParser()

    def extract_from_file(self, file_path: Path, source_doc: str = None) -> List[EntitySummary]:
        """Extract entities from a markdown file"""
        sections = self.parser.parse_file(file_path)
        source = source_doc or file_path.stem
        return self._extract_from_sections(sections, source)

    def extract_from_content(self, content: str, source_doc: str = "unknown") -> List[EntitySummary]:
        """Extract entities from markdown content"""
        sections = self.parser.parse_content(content)
        return self._extract_from_sections(sections, source_doc)

    def _extract_from_sections(self, sections: List[ParsedSection], source_doc: str) -> List[EntitySummary]:
        """Extract entities from parsed sections"""
        entities = []
        flat_sections = self.parser.flatten_sections(sections)

        for section in flat_sections:
            entity = self._section_to_entity(section, source_doc)
            if entity:
                entities.append(entity)

        return entities

    def _section_to_entity(self, section: ParsedSection, source_doc: str) -> Optional[EntitySummary]:
        """Convert a section to an entity if appropriate"""
        # Skip very short sections or meta sections
        if len(section.content) < 20:
            return None

        # Determine entity type from title
        entity_type = self._infer_entity_type(section.title, section.content)

        # Generate summary (first ~150 chars of content or use LLM later)
        summary = self._generate_summary(section.content)

        # Extract tags from title and content
        tags = self._extract_tags(section.title, section.content)

        return EntitySummary(
            id=str(uuid.uuid4()),
            name=section.title,
            entity_type=entity_type,
            summary=summary,
            tags=tags,
            source_doc=source_doc
        )

    def _infer_entity_type(self, title: str, content: str) -> EntityType:
        """Infer entity type from title and content keywords"""
        text = (title + " " + content).lower()

        for entity_type, keywords in self.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return entity_type

        # Default to scene concept for unclassified
        return EntityType.SCENE_CONCEPT

    def _generate_summary(self, content: str, max_length: int = 180) -> str:
        """Generate a brief summary from content"""
        # Simple extraction: first sentence or first N chars
        # In production, use LLM for better summaries
        content = content.strip()

        # Try to get first sentence
        sentences = content.split('.')
        if sentences and len(sentences[0]) > 10:
            summary = sentences[0].strip() + '.'
            if len(summary) <= max_length:
                return summary

        # Fallback to truncation
        if len(content) <= max_length:
            return content
        return content[:max_length-3] + '...'

    def _extract_tags(self, title: str, content: str) -> List[str]:
        """Extract relevant tags from text"""
        tags = []
        text = (title + " " + content).lower()

        # Add matched entity type keywords as tags
        for entity_type, keywords in self.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text and keyword not in tags:
                    tags.append(keyword)
                    break

        return tags[:5]  # Limit to 5 tags


def build_registry(
    worldbuilding_path: Optional[Path] = None,
    characters_path: Optional[Path] = None,
    scenes_path: Optional[Path] = None
) -> EntityRegistry:
    """Build entity registry from document files"""
    extractor = EntityExtractor()
    registry = EntityRegistry()

    if worldbuilding_path and worldbuilding_path.exists():
        entities = extractor.extract_from_file(worldbuilding_path, "worldbuilding")
        for entity in entities:
            registry.add(entity)

    if characters_path and characters_path.exists():
        entities = extractor.extract_from_file(characters_path, "characters")
        for entity in entities:
            registry.add(entity)

    if scenes_path and scenes_path.exists():
        entities = extractor.extract_from_file(scenes_path, "scenes")
        for entity in entities:
            registry.add(entity)

    return registry
