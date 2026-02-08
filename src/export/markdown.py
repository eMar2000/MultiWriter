"""Markdown export functionality"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from src.models import NovelOutline, Genre, StoryStructure


def _resolve_entity_name(registry, entity_id: str) -> str:
    """Resolve entity ID to display name for export. Returns name or entity_id/Unknown."""
    if not registry or not entity_id:
        return entity_id or "Unknown"
    entity = registry.get(entity_id)
    return entity.name if entity else (entity_id if entity_id else "Unknown")


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

        # STORY ARCS (Main outline content - put this first)
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

        # SCENES (Main outline content - put this after arcs)
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

                # Characters (resolve IDs to names for display)
                registry = outline.entity_registry if hasattr(outline, "entity_registry") else None
                if scene_pov:
                    pov_display = _resolve_entity_name(registry, scene_pov)
                    lines.append(f"**POV Character:** {pov_display}")
                if scene_chars:
                    if registry:
                        chars_display = [_resolve_entity_name(registry, c) for c in (scene_chars if isinstance(scene_chars, list) else [])]
                        chars_str = ", ".join(chars_display)
                    else:
                        chars_str = ", ".join(scene_chars) if isinstance(scene_chars, list) else str(scene_chars)
                    lines.append(f"**Characters Present:** {chars_str}")

                lines.append("")

                # Location and time (resolve location ID to name)
                if scene_location:
                    loc_display = _resolve_entity_name(registry, scene_location)
                    lines.append(f"**Location:** {loc_display}")
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

        # Plot Structure (for interactive workflow - keep for compatibility)
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

        # No appendix: entity registry and reference material stay in RAG / outline model;
        # the written file is premise, arcs, and scene outlines with names resolved from registry.
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
