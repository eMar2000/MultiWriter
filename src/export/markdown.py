"""Markdown export functionality"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from src.models import NovelOutline, Genre, StoryStructure


class MarkdownExporter:
    """Exports novel outlines to Markdown format"""

    def export(self, outline: NovelOutline) -> str:
        """
        Export outline to Markdown format

        Args:
            outline: Novel outline to export

        Returns:
            Markdown string
        """
        lines = []

        # Title and metadata
        lines.append(f"# {outline.input.premise[:60]}...")
        lines.append("")
        lines.append(f"**Genre:** {outline.input.genre.value if isinstance(outline.input.genre, Genre) else outline.input.genre}")
        lines.append(f"**Created:** {outline.created_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(outline.created_at, datetime) else outline.created_at}")
        lines.append(f"**Status:** {outline.status}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Premise
        lines.append("## Premise")
        lines.append("")
        lines.append(outline.input.premise)
        lines.append("")

        # Theme
        if outline.theme:
            lines.append("## Theme & Premise")
            lines.append("")
            lines.append(f"**Theme Question:** {outline.theme.theme_question}")
            lines.append("")
            lines.append(f"**Moral Argument:** {outline.theme.moral_argument}")
            lines.append("")
            if outline.theme.thematic_constraints:
                lines.append("**Thematic Constraints:**")
                for constraint in outline.theme.thematic_constraints:
                    lines.append(f"- {constraint}")
                lines.append("")

        # Plot Structure
        if outline.plot_structure:
            lines.append("## Plot Structure")
            lines.append("")
            structure_type = outline.plot_structure.structure_type
            if isinstance(structure_type, StoryStructure):
                structure_type = structure_type.value.replace("_", " ").title()
            lines.append(f"**Structure Type:** {structure_type}")
            lines.append("")

            # Acts
            if outline.plot_structure.acts:
                lines.append("### Acts")
                lines.append("")
                for act in outline.plot_structure.acts:
                    act_num = act.get("act_number", "?")
                    act_name = act.get("name", "Unknown")
                    lines.append(f"**Act {act_num}: {act_name}**")
                    lines.append("")
                    lines.append(act.get("description", "No description"))
                    lines.append("")

            # Plot Beats
            if outline.plot_structure.beats:
                lines.append("### Plot Beats")
                lines.append("")
                for beat in outline.plot_structure.beats:
                    beat_num = beat.beat_number
                    beat_name = beat.beat_name
                    lines.append(f"#### Beat {beat_num}: {beat_name}")
                    lines.append("")
                    lines.append(beat.description)
                    lines.append("")
                    lines.append(f"**Purpose:** {beat.purpose}")
                    lines.append(f"**Tension Level:** {beat.tension_level:.2f}")
                    if beat.required_elements:
                        lines.append("**Required Elements:**")
                        for elem in beat.required_elements:
                            lines.append(f"- {elem}")
                    lines.append("")

            # Midpoint and Reversals
            if outline.plot_structure.midpoint:
                lines.append("### Midpoint")
                lines.append("")
                lines.append(outline.plot_structure.midpoint)
                lines.append("")

            if outline.plot_structure.reversals:
                lines.append("### Key Reversals")
                lines.append("")
                for i, reversal in enumerate(outline.plot_structure.reversals, 1):
                    lines.append(f"{i}. {reversal}")
                lines.append("")

        # Characters
        if outline.characters:
            lines.append("## Characters")
            lines.append("")
            for char in outline.characters:
                char_name = char.get("name", "Unknown")
                char_role = char.get("role", "unknown")
                lines.append(f"### {char_name} ({char_role})")
                lines.append("")

                if char.get("want"):
                    lines.append(f"**Want:** {char['want']}")
                if char.get("need"):
                    lines.append(f"**Need:** {char['need']}")
                if char.get("lie"):
                    lines.append(f"**Lie:** {char['lie']}")
                if char.get("fear"):
                    lines.append(f"**Fear:** {char['fear']}")

                lines.append("")

                if char.get("arc_type"):
                    lines.append(f"**Arc:** {char['arc_type']} - From {char.get('starting_point', 'unknown')} to {char.get('ending_point', 'unknown')}")
                    lines.append("")

                if char.get("personality_summary"):
                    lines.append(f"**Personality:** {char['personality_summary']}")
                    lines.append("")

                if char.get("story_function"):
                    lines.append(f"**Story Function:** {char['story_function']}")
                    lines.append("")

                # Relationships
                if char.get("relationships"):
                    lines.append("**Relationships:**")
                    for other_char, relationship in char['relationships'].items():
                        lines.append(f"- {other_char}: {relationship}")
                    lines.append("")

        # World Building
        if outline.world_rules:
            world = outline.world_rules
            lines.append("## World Building")
            lines.append("")

            # Rules
            if world.get("rules"):
                lines.append("### World Rules")
                lines.append("")
                for rule in world["rules"]:
                    if isinstance(rule, dict):
                        rule_text = rule.get("rule", "Unknown rule")
                        category = rule.get("category", "general")
                        lines.append(f"**{category.upper()}:** {rule_text}")
                        if rule.get("explanation"):
                            lines.append(f"  *{rule['explanation']}*")
                    else:
                        lines.append(f"- {rule}")
                lines.append("")

            # Magic Systems
            if world.get("magic_systems"):
                lines.append("### Magic/Technology Systems")
                lines.append("")
                for system in world["magic_systems"]:
                    if isinstance(system, dict):
                        system_name = system.get("system_name", "Unknown System")
                        hardness = system.get("hardness", "unknown")
                        lines.append(f"**{system_name}** ({hardness} system)")
                        if system.get("description"):
                            lines.append(f"{system['description']}")
                        lines.append("")

            # Locations
            if world.get("locations"):
                lines.append("### Locations")
                lines.append("")
                for location in world["locations"]:
                    if isinstance(location, dict):
                        loc_name = location.get("name", "Unknown Location")
                        loc_type = location.get("type", "unknown")
                        lines.append(f"**{loc_name}** ({loc_type})")
                        if location.get("description"):
                            lines.append(location["description"])
                        lines.append("")

            # Timeline
            if world.get("timeline"):
                lines.append("### Timeline")
                lines.append("")
                for event in world["timeline"]:
                    if isinstance(event, dict):
                        event_name = event.get("name", "Unknown Event")
                        time_period = event.get("time_period", "Unknown time")
                        lines.append(f"**{time_period}:** {event_name}")
                        if event.get("description"):
                            lines.append(f"  {event['description']}")
                        lines.append("")

        # Scenes
        if outline.scenes:
            lines.append("## Scene Outlines")
            lines.append("")

            for scene in outline.scenes:
                scene_num = scene.get("scene_number", "?")
                scene_title = scene.get("title", f"Scene {scene_num}")
                scene_type = scene.get("scene_type", "action")

                lines.append(f"### Scene {scene_num}: {scene_title} ({scene_type})")
                lines.append("")

                if scene.get("goal"):
                    lines.append(f"**Goal:** {scene['goal']}")
                if scene.get("conflict"):
                    lines.append(f"**Conflict:** {scene['conflict']}")
                if scene.get("outcome"):
                    lines.append(f"**Outcome:** {scene['outcome']}")
                if scene.get("stakes"):
                    lines.append(f"**Stakes:** {scene['stakes']}")

                lines.append("")

                # Characters
                if scene.get("pov_character"):
                    lines.append(f"**POV Character:** {scene['pov_character']}")
                if scene.get("characters_present"):
                    lines.append(f"**Characters Present:** {', '.join(scene['characters_present'])}")

                lines.append("")

                # Location and time
                if scene.get("location_id"):
                    lines.append(f"**Location:** {scene['location_id']}")
                if scene.get("time_period"):
                    lines.append(f"**Time:** {scene['time_period']}")

                lines.append("")

                # Scene beats
                if scene.get("beats"):
                    lines.append("**Scene Beats:**")
                    for beat in scene["beats"]:
                        if isinstance(beat, dict):
                            beat_num = beat.get("beat_number", "?")
                            beat_desc = beat.get("description", "No description")
                            lines.append(f"{beat_num}. {beat_desc}")
                    lines.append("")

                # Tension
                tension_start = scene.get("tension_start", 0)
                tension_end = scene.get("tension_end", 0)
                lines.append(f"**Tension:** {tension_start:.2f} → {tension_end:.2f}")
                lines.append("")

        # Metadata
        if outline.metadata:
            lines.append("---")
            lines.append("")
            lines.append("## Metadata")
            lines.append("")
            for key, value in outline.metadata.items():
                lines.append(f"**{key}:** {value}")
            lines.append("")

        return "\n".join(lines)

    def export_to_file(self, outline: NovelOutline, file_path: Path):
        """
        Export outline to a file

        Args:
            outline: Novel outline to export
            file_path: Path to output file
        """
        markdown_content = self.export(outline)

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
