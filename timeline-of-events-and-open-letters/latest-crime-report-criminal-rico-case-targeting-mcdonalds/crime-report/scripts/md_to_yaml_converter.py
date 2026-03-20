#!/usr/bin/env python3
"""
MD to YAML Converter for Crime Report
=====================================

Converts a single large Markdown file into structured YAML section files.
Each section (## or ###) becomes its own YAML file in the sections/ folder.

Usage:
    python md_to_yaml_converter.py <input.md> [--output-dir sections/]

The converter:
1. Extracts Hugo frontmatter → frontmatter.yaml
2. Extracts CSS styles → styles.yaml
3. Extracts Table of Contents → toc.yaml
4. Splits content by ## and ### headers → individual section files
5. Extracts footnotes → footnotes.yaml
"""

import re
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class MarkdownToYAMLConverter:
    def __init__(self, input_file: str, output_dir: str = "sections"):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.content = ""
        self.frontmatter = {}
        self.sections = []

    def read_file(self) -> str:
        """Read the input markdown file."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.content = f.read()
        return self.content

    def extract_frontmatter(self) -> Tuple[Dict, str]:
        """Extract YAML frontmatter from markdown."""
        frontmatter_pattern = r'^---\n(.*?)\n---\n'
        match = re.match(frontmatter_pattern, self.content, re.DOTALL)

        if match:
            frontmatter_str = match.group(1)
            remaining_content = self.content[match.end():]

            # Parse YAML frontmatter
            try:
                self.frontmatter = yaml.safe_load(frontmatter_str)
            except yaml.YAMLError:
                # If YAML parsing fails, store as raw string
                self.frontmatter = {'raw': frontmatter_str}

            return self.frontmatter, remaining_content

        return {}, self.content

    def extract_styles(self, content: str) -> Tuple[str, str]:
        """Extract CSS style blocks."""
        style_pattern = r'<style>(.*?)</style>'
        match = re.search(style_pattern, content, re.DOTALL)

        styles = ""
        if match:
            styles = match.group(0)  # Include <style> tags
            content = content[:match.start()] + content[match.end():]

        return styles, content

    def extract_toc(self, content: str) -> Tuple[str, str]:
        """Extract Table of Contents div."""
        # Match the manual-toc div including nested content
        toc_pattern = r'<div class="manual-toc"[^>]*>.*?</div>\s*</div>'
        match = re.search(toc_pattern, content, re.DOTALL)

        toc = ""
        if match:
            toc = match.group(0)
            content = content[:match.start()] + content[match.end():]
        else:
            # Try simpler pattern
            toc_pattern = r'<div class="manual-toc".*?## TABLE OF CONTENTS.*?</ul>\s*</li>\s*</ul>\s*</div>'
            match = re.search(toc_pattern, content, re.DOTALL)
            if match:
                toc = match.group(0)
                content = content[:match.start()] + content[match.end():]

        return toc, content

    def extract_footnotes(self, content: str) -> Tuple[str, str]:
        """Extract footnotes at the end of the document."""
        # Footnotes typically start with [^something]:
        footnote_pattern = r'\n(\[\^[^\]]+\]:.*?)(?=\n\n[^[]|\Z)'

        footnotes = []
        for match in re.finditer(footnote_pattern, content, re.DOTALL):
            footnotes.append(match.group(1).strip())

        # Also match the block of footnotes at the end
        end_footnotes_pattern = r'\n(\[\^[^\]]+\]:[^\n]*\n?)+'
        matches = list(re.finditer(end_footnotes_pattern, content))

        footnotes_text = ""
        if matches:
            # Get the last block of footnotes
            last_match = matches[-1]
            footnotes_text = last_match.group(0).strip()
            # Remove from content
            content = content[:last_match.start()] + content[last_match.end():]

        return footnotes_text, content

    def extract_intro_text(self, content: str) -> Tuple[str, str]:
        """Extract introductory text before the first major section."""
        # Find the first ## heading
        first_section_match = re.search(r'^##\s+', content, re.MULTILINE)

        intro_text = ""
        if first_section_match:
            intro_text = content[:first_section_match.start()].strip()
            content = content[first_section_match.start():]

        return intro_text, content

    def parse_section_id(self, header: str) -> str:
        """
        Generate a section ID from a header.
        Examples:
            "## TLDR; EXECUTIVE SUMMARY" -> "executive-summary"
            "### (I)(A) Witness Tampering..." -> "I-A"
            "## (IV) Non-exhaustive List..." -> "IV-intro"
        """
        # Check for section pattern like (I)(A), (IV)(EE), etc.
        section_match = re.search(r'\(([IVX]+)\)\(([A-Z]+)\)', header)
        if section_match:
            return f"{section_match.group(1)}-{section_match.group(2)}"

        # Check for main section pattern like (I), (IV), etc.
        main_section_match = re.search(r'\(([IVX]+)\)\s', header)
        if main_section_match:
            return f"{main_section_match.group(1)}-intro"

        # Special cases
        if "EXECUTIVE SUMMARY" in header.upper():
            return "executive-summary"
        if "PREAMBLE" in header.upper():
            return "preamble"
        if "TABLE OF CONTENTS" in header.upper():
            return "toc"

        # Generate from header text
        # Remove markdown formatting and special characters
        clean = re.sub(r'[#\{\}"\'\[\]<>]', '', header)
        clean = re.sub(r'\s+', '-', clean.strip().lower())
        clean = re.sub(r'[^a-z0-9-]', '', clean)
        clean = re.sub(r'-+', '-', clean)
        return clean[:50]  # Limit length

    def split_into_sections(self, content: str) -> List[Dict]:
        """Split content into sections based on ## and ### headers."""
        sections = []

        # Pattern to match ## or ### headers
        header_pattern = r'^(#{2,3})\s+(.+?)(?:\s*\{[^}]+\})?\s*$'

        lines = content.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                # Save previous section
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # Extract id if present
                id_match = re.search(r'\{id="([^"]+)"\}', line)
                anchor_id = id_match.group(1) if id_match else None

                section_id = self.parse_section_id(line)

                current_section = {
                    'id': section_id,
                    'level': level,
                    'title': title,
                    'anchor_id': anchor_id,
                    'raw_header': line
                }
                current_content = []
            else:
                current_content.append(line)

        # Don't forget the last section
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)

        return sections

    def section_to_yaml(self, section: Dict) -> Dict:
        """Convert a section dict to YAML-friendly format."""
        return {
            'id': section['id'],
            'level': section['level'],
            'title': section['title'],
            'anchor_id': section.get('anchor_id'),
            'raw_header': section['raw_header'],
            'content': section['content']
        }

    def write_yaml_file(self, filename: str, data: Dict, content_key: str = None):
        """Write data to a YAML file."""
        filepath = self.output_dir / filename

        # Custom representer for multi-line strings
        def str_representer(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)

        yaml.add_representer(str, str_representer)

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

        print(f"  Created: {filepath}")

    def write_raw_file(self, filename: str, content: str):
        """Write raw content (like styles) to a YAML file with content block."""
        filepath = self.output_dir / filename

        data = {'content': content}

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# This file contains raw content that will be included as-is\n")
            f.write("content: |\n")
            for line in content.split('\n'):
                f.write(f"  {line}\n")

        print(f"  Created: {filepath}")

    def convert(self):
        """Main conversion process."""
        print(f"Converting: {self.input_file}")
        print(f"Output dir: {self.output_dir}")
        print()

        # Read the file
        self.read_file()
        content = self.content

        # 1. Extract frontmatter
        print("Extracting frontmatter...")
        frontmatter, content = self.extract_frontmatter()
        self.write_yaml_file("frontmatter.en.yaml", {'frontmatter': frontmatter})

        # 2. Extract styles
        print("Extracting styles...")
        styles, content = self.extract_styles(content)
        if styles:
            self.write_raw_file("styles.en.yaml", styles)

        # 3. Extract intro text (before TOC)
        intro_text, content = self.extract_intro_text(content)
        if intro_text:
            self.write_raw_file("intro-text.en.yaml", intro_text)

        # 4. Extract TOC
        print("Extracting table of contents...")
        toc, content = self.extract_toc(content)
        if toc:
            self.write_raw_file("toc.en.yaml", toc)

        # 5. Extract footnotes
        print("Extracting footnotes...")
        footnotes, content = self.extract_footnotes(content)
        if footnotes:
            self.write_raw_file("footnotes.en.yaml", footnotes)

        # 6. Split remaining content into sections
        print("Splitting into sections...")
        sections = self.split_into_sections(content)

        print(f"\nFound {len(sections)} sections:")

        # Track section IDs to handle duplicates
        id_counts = {}

        for section in sections:
            section_id = section['id']

            # Handle duplicate IDs
            if section_id in id_counts:
                id_counts[section_id] += 1
                section_id = f"{section_id}-{id_counts[section_id]}"
            else:
                id_counts[section_id] = 1

            filename = f"{section_id}.en.yaml"

            yaml_data = self.section_to_yaml(section)
            self.write_yaml_file(filename, yaml_data)

        print(f"\nConversion complete!")
        print(f"Total files created: {len(sections) + 4}")  # +4 for frontmatter, styles, toc, footnotes


def main():
    if len(sys.argv) < 2:
        print("Usage: python md_to_yaml_converter.py <input.md> [--output-dir sections/]")
        print()
        print("Example:")
        print("  python md_to_yaml_converter.py working_copy_index.en.md --output-dir sections/")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = "sections"

    # Parse optional arguments
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    converter = MarkdownToYAMLConverter(input_file, output_dir)
    converter.convert()


if __name__ == "__main__":
    main()
