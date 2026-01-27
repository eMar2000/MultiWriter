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
        premise_text = "Generated from documents"
        genre_text = "Unknown"
        if outline.input:
            premise_text = outline.input.premise[:60] + "..." if len(outline.input.premise) > 60 else outline.input.premise
            if isinstance(outline.input.genre, Genre):
                genre_text = outline.input.genre.value
            else:
                genre_text = str(outline.input.genre) if outline.input.genre else "Unknown"

        lines.append(f"# {premise_text}")
        lines.append("")
        lines.append(f"**Genre:** {genre_text}")

        created_at_str = outline.created_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(outline.created_at, datetime) else str(outline.created_at)
        lines.append(f"**Created:** {created_at_str}")
        lines.append(f"**Status:** {outline.status}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Premise
        if outline.input and outline.input.premise:
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
            acts = outline.plot_structure.acts if outline.plot_structure.acts else []
            if acts:
                lines.append("### Acts")
                lines.append("")
                for act in acts:
                    if isinstance(act, dict):
                        act_num = act.get("act_number", "?")
                        act_name = act.get("name", "Unknown")
                        act_desc = act.get("description", "No description")
                    else:
                        act_num = getattr(act, "act_number", "?")
                        act_name = getattr(act, "name", "Unknown")
                        act_desc = getattr(act, "description", "No description")
                    lines.append(f"**Act {act_num}: {act_name}**")
                    lines.append("")
                    lines.append(act_desc)
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
                # Handle both Pydantic models and dicts (from serialization)
                if isinstance(char, dict):
                    char_name = char.get("name", "Unknown")
                    char_role = char.get("role", "unknown")
                    char_want = char.get("want")
                    char_need = char.get("need")
                    char_lie = char.get("lie")
                    char_fear = char.get("fear")
                    char_arc_type = char.get("arc_type")
                    char_starting = char.get("starting_point", "unknown")
                    char_ending = char.get("ending_point", "unknown")
                    char_personality = char.get("personality_summary")
                    char_function = char.get("story_function")
                    char_relationships = char.get("relationships")
                else:
                    # Pydantic model
                    char_name = char.name if char.name else "Unknown"
                    char_role = char.role if char.role else "unknown"
                    char_want = char.want
                    char_need = char.need
                    char_lie = char.lie
                    char_fear = char.fear
                    char_arc_type = char.arc_type.value if char.arc_type else None
                    char_starting = char.starting_point if char.starting_point else "unknown"
                    char_ending = char.ending_point if char.ending_point else "unknown"
                    char_personality = char.personality_summary
                    char_function = char.story_function
                    char_relationships = char.relationships

                lines.append(f"### {char_name} ({char_role})")
                lines.append("")

                if char_want:
                    lines.append(f"**Want:** {char_want}")
                if char_need:
                    lines.append(f"**Need:** {char_need}")
                if char_lie:
                    lines.append(f"**Lie:** {char_lie}")
                if char_fear:
                    lines.append(f"**Fear:** {char_fear}")

                lines.append("")

                if char_arc_type:
                    lines.append(f"**Arc:** {char_arc_type} - From {char_starting} to {char_ending}")
                    lines.append("")

                if char_personality:
                    lines.append(f"**Personality:** {char_personality}")
                    lines.append("")

                if char_function:
                    lines.append(f"**Story Function:** {char_function}")
                    lines.append("")

                # Relationships
                if char_relationships:
                    lines.append("**Relationships:**")
                    for other_char, relationship in char_relationships.items():
                        lines.append(f"- {other_char}: {relationship}")
                    lines.append("")

        # World Building
        if outline.world_rules:
            world = outline.world_rules
            lines.append("## World Building")
            lines.append("")

            # Rules
            world_rules = world.rules if hasattr(world, 'rules') else world.get("rules", []) if isinstance(world, dict) else []
            if world_rules:
                lines.append("### World Rules")
                lines.append("")
                for rule in world_rules:
                    if isinstance(rule, dict):
                        rule_text = rule.get("rule", "Unknown rule")
                        category = rule.get("category", "general")
                        explanation = rule.get("explanation")
                    else:
                        # Pydantic WorldRule model
                        rule_text = rule.rule
                        category = rule.category if rule.category else "general"
                        explanation = rule.explanation

                    lines.append(f"**{category.upper()}:** {rule_text}")
                    if explanation:
                        lines.append(f"  *{explanation}*")
                lines.append("")

            # Magic Systems
            magic_systems = world.magic_systems if hasattr(world, 'magic_systems') else world.get("magic_systems", []) if isinstance(world, dict) else []
            if magic_systems:
                lines.append("### Magic/Technology Systems")
                lines.append("")
                for system in magic_systems:
                    if isinstance(system, dict):
                        system_name = system.get("system_name", "Unknown System")
                        hardness = system.get("hardness", "unknown")
                        description = system.get("description")
                    else:
                        # Pydantic MagicSystem model
                        system_name = system.system_name
                        hardness = system.hardness if system.hardness else "unknown"
                        description = system.description

                    lines.append(f"**{system_name}** ({hardness} system)")
                    if description:
                        lines.append(description)
                    lines.append("")

            # Locations
            locations = world.locations if hasattr(world, 'locations') else world.get("locations", []) if isinstance(world, dict) else []
            if locations:
                lines.append("### Locations")
                lines.append("")
                for location in locations:
                    if isinstance(location, dict):
                        loc_name = location.get("name", "Unknown Location")
                        loc_type = location.get("type", "unknown")
                        loc_desc = location.get("description")
                    else:
                        # Pydantic Location model
                        loc_name = location.name
                        loc_type = location.type if location.type else "unknown"
                        loc_desc = location.description

                    lines.append(f"**{loc_name}** ({loc_type})")
                    if loc_desc:
                        lines.append(loc_desc)
                    lines.append("")

            # Timeline
            timeline = world.timeline if hasattr(world, 'timeline') else world.get("timeline", []) if isinstance(world, dict) else []
            if timeline:
                lines.append("### Timeline")
                lines.append("")
                for event in timeline:
                    if isinstance(event, dict):
                        event_name = event.get("name", "Unknown Event")
                        time_period = event.get("time_period", "Unknown time")
                        event_desc = event.get("description")
                    else:
                        # Pydantic TimelineEvent model
                        event_name = event.name
                        time_period = event.time_period
                        event_desc = event.description

                    lines.append(f"**{time_period}:** {event_name}")
                    if event_desc:
                        lines.append(f"  {event_desc}")
                    lines.append("")

        # Entity Registry (NEW - for document-driven outlines)
        if outline.entity_registry:
            lines.append("## Entity Registry")
            lines.append("")
            lines.append(f"**Total Entities:** {len(outline.entity_registry.entities)}")
            lines.append("")

            # Group by type
            from src.models import EntityType
            for entity_type in EntityType:
                entities_of_type = outline.entity_registry.get_by_type(entity_type)
                if entities_of_type:
                    # entity_type is an enum, get its value
                    type_name = entity_type.value.title()
                    lines.append(f"### {type_name}s ({len(entities_of_type)})")
                    lines.append("")
                    for entity in entities_of_type[:10]:  # Limit to first 10 per type
                        lines.append(f"- **{entity.name}**: {entity.summary}")
                    if len(entities_of_type) > 10:
                        lines.append(f"  *... and {len(entities_of_type) - 10} more*")
                    lines.append("")

        # Arcs and Relationships (NEW - for document-driven outlines)
        if outline.relationships and isinstance(outline.relationships, dict):
            arcs = outline.relationships.get("arcs", [])
            if arcs:
                lines.append("## Story Arcs")
                lines.append("")
                for arc in arcs:
                    arc_name = arc.get("name", "Unnamed Arc") if isinstance(arc, dict) else getattr(arc, "name", "Unnamed Arc")
                    arc_desc = arc.get("description", "") if isinstance(arc, dict) else getattr(arc, "description", "")
                    arc_type = arc.get("type", "main") if isinstance(arc, dict) else getattr(arc, "type", "main")
                    lines.append(f"### {arc_name} ({arc_type})")
                    lines.append("")
                    if arc_desc:
                        lines.append(arc_desc)
                        lines.append("")

                timeline = outline.relationships.get("timeline", [])
                if timeline:
                    lines.append("### Arc Timeline")
                    lines.append("")
                    for i, arc_id in enumerate(timeline, 1):
                        lines.append(f"{i}. {arc_id}")
                    lines.append("")

        # Scenes
        if outline.scenes:
            lines.append("## Scene Outlines")
            lines.append("")

            for scene in outline.scenes:
                # Handle both Pydantic models and dicts
                if isinstance(scene, dict):
                    scene_num = scene.get("scene_number", "?")
                    scene_title = scene.get("title", f"Scene {scene_num}")
                    scene_type = scene.get("scene_type", "action")
                    scene_goal = scene.get("goal")
                    scene_conflict = scene.get("conflict")
                    scene_outcome = scene.get("outcome")
                    scene_stakes = scene.get("stakes")
                    scene_pov = scene.get("pov_character")
                    scene_chars = scene.get("characters_present", [])
                    scene_location = scene.get("location_id")
                    scene_time = scene.get("time_period")
                    scene_beats = scene.get("beats", [])
                    tension_start = scene.get("tension_start", 0)
                    tension_end = scene.get("tension_end", 0)
                else:
                    # Pydantic model
                    scene_num = scene.scene_number if scene.scene_number else "?"
                    scene_title = scene.title if scene.title else f"Scene {scene_num}"
                    scene_type = scene.scene_type.value if scene.scene_type else "action"
                    scene_goal = scene.goal
                    scene_conflict = scene.conflict
                    scene_outcome = scene.outcome
                    scene_stakes = scene.stakes
                    scene_pov = scene.pov_character
                    scene_chars = scene.characters_present if scene.characters_present else []
                    scene_location = scene.location_id
                    scene_time = scene.time_period
                    scene_beats = scene.beats if scene.beats else []
                    tension_start = scene.tension_start if scene.tension_start else 0
                    tension_end = scene.tension_end if scene.tension_end else 0

                lines.append(f"### Scene {scene_num}: {scene_title} ({scene_type})")
                lines.append("")

                if scene_goal:
                    lines.append(f"**Goal:** {scene_goal}")
                if scene_conflict:
                    lines.append(f"**Conflict:** {scene_conflict}")
                if scene_outcome:
                    lines.append(f"**Outcome:** {scene_outcome}")
                if scene_stakes:
                    lines.append(f"**Stakes:** {scene_stakes}")

                lines.append("")

                # Characters
                if scene_pov:
                    lines.append(f"**POV Character:** {scene_pov}")
                if scene_chars:
                    chars_str = ', '.join(scene_chars) if isinstance(scene_chars, list) else str(scene_chars)
                    lines.append(f"**Characters Present:** {chars_str}")

                lines.append("")

                # Location and time
                if scene_location:
                    lines.append(f"**Location:** {scene_location}")
                if scene_time:
                    lines.append(f"**Time:** {scene_time}")

                lines.append("")

                # Scene beats
                if scene_beats:
                    lines.append("**Scene Beats:**")
                    for beat in scene_beats:
                        if isinstance(beat, dict):
                            beat_num = beat.get("beat_number", "?")
                            beat_desc = beat.get("description", "No description")
                        else:
                            beat_num = beat.beat_number if beat.beat_number else "?"
                            beat_desc = beat.description if beat.description else "No description"
                        lines.append(f"{beat_num}. {beat_desc}")
                    lines.append("")

                # Tension
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
