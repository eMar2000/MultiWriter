"""Markdown document parser"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    """A parsed section from a markdown document"""
    title: str
    level: int  # 1-4 for headers, 0 for body
    content: str
    children: List['ParsedSection'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_line: int = 0
    end_line: int = 0


class DocumentParser:
    """Parse markdown documents into structured sections"""

    def __init__(self):
        # Support both markdown headers (# Title) and bracket notation ([Title])
        self.header_pattern = re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE)
        self.bracket_pattern = re.compile(r'^\[([^\]]+)\]$', re.MULTILINE)

    def parse_file(self, file_path: Path) -> List[ParsedSection]:
        """Parse a markdown file into sections

        Args:
            file_path: Path to markdown file

        Returns:
            List of parsed sections with hierarchy

        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file is not valid UTF-8
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse_content(content)

    def parse_content(self, content: str) -> List[ParsedSection]:
        """Parse markdown content into hierarchical sections

        Args:
            content: Markdown content string

        Returns:
            List of top-level ParsedSection objects with nested children
        """
        lines = content.split('\n')
        sections = []
        section_stack = []  # Stack to track hierarchy

        i = 0
        while i < len(lines):
            line = lines[i]
            header_match = self.header_pattern.match(line)
            bracket_match = self.bracket_pattern.match(line.strip())

            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # Collect content until next header
                content_lines = []
                j = i + 1
                while j < len(lines):
                    next_header = self.header_pattern.match(lines[j])
                    next_bracket = self.bracket_pattern.match(lines[j].strip())
                    if next_header or next_bracket:
                        break
                    content_lines.append(lines[j])
                    j += 1

                section = ParsedSection(
                    title=title,
                    level=level,
                    content='\n'.join(content_lines).strip(),
                    children=[],
                    metadata={'source_line': i + 1},
                    start_line=i + 1,
                    end_line=j
                )

                # Build hierarchy
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()

                if section_stack:
                    section_stack[-1].children.append(section)
                else:
                    sections.append(section)

                section_stack.append(section)
                i = j
            elif bracket_match:
                # Handle bracket notation [Title] as level 2 headers
                title = bracket_match.group(1).strip()
                level = 2  # Treat bracket sections as level 2

                # Collect content until next header or bracket
                content_lines = []
                j = i + 1
                while j < len(lines):
                    next_header = self.header_pattern.match(lines[j])
                    next_bracket = self.bracket_pattern.match(lines[j].strip())
                    if next_header or next_bracket:
                        break
                    content_lines.append(lines[j])
                    j += 1

                section = ParsedSection(
                    title=title,
                    level=level,
                    content='\n'.join(content_lines).strip(),
                    children=[],
                    metadata={'source_line': i + 1, 'format': 'bracket'},
                    start_line=i + 1,
                    end_line=j
                )

                # Build hierarchy
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()

                if section_stack:
                    section_stack[-1].children.append(section)
                else:
                    sections.append(section)

                section_stack.append(section)
                i = j
            else:
                i += 1

        return sections

    def flatten_sections(self, sections: List[ParsedSection]) -> List[ParsedSection]:
        """Flatten nested sections into a flat list"""
        result = []
        for section in sections:
            result.append(section)
            result.extend(self.flatten_sections(section.children))
        return result
