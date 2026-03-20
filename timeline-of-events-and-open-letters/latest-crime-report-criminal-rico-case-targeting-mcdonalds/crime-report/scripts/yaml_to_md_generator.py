#!/usr/bin/env python3
"""
YAML to Markdown Generator for Crime Report
============================================

Assembles YAML section files into a single Markdown file for Hugo.
Respects the meta.yaml structure and status fields to control output.

Features:
- Reads section order from meta.yaml
- Skips sections with status: draft or status: review
- Auto-numbers paragraphs with continuous thesis-style: (DRAFT#XX)(1), (DRAFT#XX)(2), etc.
- Outputs a single markdown file ready for Hugo

Usage:
    python yaml_to_md_generator.py [--meta meta.yaml] [--sections sections/] [--output output.md]

Statuses:
    - published: Included in output
    - draft: Skipped (work in progress)
    - review: Skipped (under review)
"""

import re
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class YAMLToMarkdownGenerator:
    def __init__(self, meta_file: str = "meta.yaml", sections_dir: str = "sections", output_file: str = None):
        self.meta_file = Path(meta_file)
        self.sections_dir = Path(sections_dir)
        self.meta = {}
        self.output_file = output_file

        # Global paragraph counter for continuous numbering
        self.paragraph_counter = 0

    def load_meta(self) -> Dict:
        """Load the meta.yaml configuration file."""
        with open(self.meta_file, 'r', encoding='utf-8') as f:
            self.meta = yaml.safe_load(f)
        return self.meta

    def load_section_file(self, section_id: str) -> Optional[Dict]:
        """Load a section YAML file by ID."""
        language = self.meta.get('language', 'en')
        filename = f"{section_id}.{language}.yaml"
        filepath = self.sections_dir / filename

        if not filepath.exists():
            print(f"  Warning: Section file not found: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def should_include_section(self, section_config: Dict) -> bool:
        """Check if a section should be included based on status."""
        status = section_config.get('status', 'published')
        return status == 'published'

    def get_draft_number(self) -> int:
        """Get the draft number from meta.yaml."""
        return self.meta.get('draft_number', 32)

    def renumber_paragraphs(self, content: str) -> str:
        """
        Re-number paragraphs using continuous thesis-style numbering.

        Transforms:
            (DRAFT#32)(1)&emsp;Text -> (DRAFT#32)(N)&emsp;Text

        where N is the global sequential paragraph number across the entire document.
        """
        draft_num = self.get_draft_number()

        def replace_paragraph_number(match):
            self.paragraph_counter += 1
            return f"(DRAFT#{draft_num})({self.paragraph_counter})&emsp;"

        # Pattern to match paragraph numbers: (DRAFT#NN)(number)&emsp;
        pattern = r'\(DRAFT#\d+\)\(\d+\)&emsp;'

        content = re.sub(pattern, replace_paragraph_number, content)

        return content

    def process_frontmatter(self, section_data: Dict) -> str:
        """Process frontmatter section into YAML front matter block."""
        if not section_data:
            return ""

        frontmatter = section_data.get('frontmatter', section_data.get('content', {}))

        if isinstance(frontmatter, str):
            # Already formatted
            return f"---\n{frontmatter}\n---\n"

        if isinstance(frontmatter, dict):
            # Convert dict to YAML
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return f"---\n{yaml_str}---\n"

        return ""

    def process_raw_content(self, section_data: Dict) -> str:
        """Process raw content sections (styles, toc, footnotes)."""
        if not section_data:
            return ""

        content = section_data.get('content', '')
        if isinstance(content, str):
            return content + "\n"
        return ""

    def process_section(self, section_data: Dict, section_id: str) -> str:
        """Process a regular content section."""
        if not section_data:
            return ""

        output_parts = []

        # Add header if present
        raw_header = section_data.get('raw_header', '')
        if raw_header:
            output_parts.append(raw_header)

        # Add content with re-numbered paragraphs
        content = section_data.get('content', '')
        if content:
            # Renumber paragraphs with continuous numbering
            content = self.renumber_paragraphs(content)
            output_parts.append(content)

        return '\n'.join(output_parts)

    def generate(self) -> str:
        """Main generation process."""
        print(f"Loading meta from: {self.meta_file}")
        self.load_meta()

        draft_num = self.get_draft_number()
        print(f"Draft number: {draft_num}")

        output_parts = []
        included_count = 0
        skipped_count = 0

        structure = self.meta.get('structure', [])
        print(f"\nProcessing {len(structure)} sections...")

        for section_config in structure:
            section_id = section_config.get('id')
            section_type = section_config.get('type', 'content')
            status = section_config.get('status', 'published')

            # Check if section should be included
            if not self.should_include_section(section_config):
                print(f"  SKIP [{status}]: {section_id}")
                skipped_count += 1
                continue

            print(f"  Include: {section_id}")
            included_count += 1

            # Load section data
            section_data = self.load_section_file(section_id)

            if section_data is None:
                print(f"    -> File not found, skipping")
                continue

            # Process based on type
            if section_type == 'frontmatter':
                output_parts.append(self.process_frontmatter(section_data))
            elif section_type in ('styles', 'toc', 'footnotes'):
                output_parts.append(self.process_raw_content(section_data))
            else:
                output_parts.append(self.process_section(section_data, section_id))

        # Combine all parts
        output = '\n'.join(filter(None, output_parts))

        print(f"\nGeneration complete!")
        print(f"  Sections included: {included_count}")
        print(f"  Sections skipped: {skipped_count}")

        return output

    def write_output(self, content: str):
        """Write the generated content to the output file."""
        output_path = self.output_file or self.meta.get('output_file', 'output.md')

        # Handle relative paths from meta.yaml
        if not os.path.isabs(output_path):
            output_path = self.meta_file.parent / output_path

        output_path = Path(output_path)

        # Create backup of existing file
        if output_path.exists():
            backup_path = output_path.with_suffix(f'.md.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            print(f"\nBacking up existing file to: {backup_path}")
            import shutil
            shutil.copy(output_path, backup_path)

        print(f"Writing output to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Output file size: {len(content):,} bytes")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Markdown from YAML section files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python yaml_to_md_generator.py
    python yaml_to_md_generator.py --meta meta.yaml --sections sections/
    python yaml_to_md_generator.py --output ../working_copy_index.en.md
    python yaml_to_md_generator.py --dry-run

Statuses in meta.yaml:
    published  - Section will be included in output
    draft      - Section will be skipped (work in progress)
    review     - Section will be skipped (under review)
        """
    )

    parser.add_argument('--meta', default='meta.yaml',
                        help='Path to meta.yaml configuration file')
    parser.add_argument('--sections', default='sections',
                        help='Path to sections directory')
    parser.add_argument('--output', default=None,
                        help='Output file path (overrides meta.yaml setting)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Process without writing output file')

    args = parser.parse_args()

    generator = YAMLToMarkdownGenerator(
        meta_file=args.meta,
        sections_dir=args.sections,
        output_file=args.output
    )

    content = generator.generate()

    if args.dry_run:
        print("\n[DRY RUN] Output would be:")
        print("-" * 40)
        print(content[:2000])
        if len(content) > 2000:
            print(f"\n... ({len(content) - 2000:,} more characters)")
    else:
        generator.write_output(content)


if __name__ == "__main__":
    main()
