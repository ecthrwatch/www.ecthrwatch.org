#!/usr/bin/env python3
"""
Renumber sections and paragraphs in the crime report.

Handles:
1. Section headers (3 levels):
   - Level 1: ## (I), ## (II), ## (III)... (Roman numerals)
   - Level 2: ### (I)(A), ### (I)(B)... (Parent Roman + uppercase letter)
   - Level 3: #### (I)(A)(a), #### (I)(A)(b)... (Parent + lowercase letter)

2. Paragraph numbers (global sequential):
   - (1), (2), (3)... (clean format)
   - Count continues across the entire document

Skips:
   - Content inside <!-- DRAFT: ... --> HTML comments
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def int_to_roman(num: int) -> str:
    """Convert integer to Roman numeral."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    roman = ''
    for i, v in enumerate(val):
        while num >= v:
            roman += syms[i]
            num -= v
    return roman


def int_to_letter(num: int, uppercase: bool = True) -> str:
    """Convert integer (1-26) to letter (A-Z or a-z)."""
    if num < 1 or num > 26:
        raise ValueError(f"Number {num} out of range for letter conversion")
    base = ord('A') if uppercase else ord('a')
    return chr(base + num - 1)


def remove_draft_sections(content: str) -> Tuple[str, list]:
    """
    Temporarily remove <!-- DRAFT: ... --> sections.
    Returns the content without drafts and a list of (placeholder, draft_content) tuples.
    """
    drafts = []
    pattern = r'(<!--\s*DRAFT:.*?-->)'

    def replace_draft(match):
        placeholder = f'__DRAFT_PLACEHOLDER_{len(drafts)}__'
        drafts.append((placeholder, match.group(1)))
        return placeholder

    content_without_drafts = re.sub(pattern, replace_draft, content, flags=re.DOTALL)
    return content_without_drafts, drafts


def restore_draft_sections(content: str, drafts: list) -> str:
    """Restore draft sections from placeholders."""
    for placeholder, draft_content in drafts:
        content = content.replace(placeholder, draft_content)
    return content


def renumber_sections(content: str) -> str:
    """
    Renumber section headers.

    Level 1: ## (I) Title -> ## (I), ## (II), etc.
    Level 2: ### (I)(A) Title -> ### (I)(A), ### (I)(B), etc.
    Level 3: #### (I)(A)(a) Title -> #### (I)(A)(a), #### (I)(A)(b), etc.
    """
    lines = content.split('\n')
    new_lines = []

    # Counters
    level1_count = 0
    level2_count = 0
    level3_count = 0

    # Current parent references
    current_level1 = ''
    current_level2 = ''

    # Patterns for section headers
    # Level 1: ## (ROMAN) or ## (ROMAN) Title
    level1_pattern = r'^(##\s+)\([IVXLCDM]+\)(.*)$'
    # Level 2: ### (ROMAN)(LETTER) or ### (ROMAN)(LETTER) Title
    level2_pattern = r'^(###\s+)\([IVXLCDM]+\)\([A-Z]\)(.*)$'
    # Level 3: #### (ROMAN)(LETTER)(letter) or #### (ROMAN)(LETTER)(letter) Title
    level3_pattern = r'^(####\s+)\([IVXLCDM]+\)\([A-Z]\)\([a-z]\)(.*)$'

    for line in lines:
        # Check Level 1
        match1 = re.match(level1_pattern, line)
        if match1:
            level1_count += 1
            level2_count = 0  # Reset child counter
            level3_count = 0
            current_level1 = int_to_roman(level1_count)
            new_line = f'{match1.group(1)}({current_level1}){match1.group(2)}'
            new_lines.append(new_line)
            continue

        # Check Level 2
        match2 = re.match(level2_pattern, line)
        if match2:
            level2_count += 1
            level3_count = 0  # Reset child counter
            current_level2 = int_to_letter(level2_count, uppercase=True)
            new_line = f'{match2.group(1)}({current_level1})({current_level2}){match2.group(2)}'
            new_lines.append(new_line)
            continue

        # Check Level 3
        match3 = re.match(level3_pattern, line)
        if match3:
            level3_count += 1
            current_level3 = int_to_letter(level3_count, uppercase=False)
            new_line = f'{match3.group(1)}({current_level1})({current_level2})({current_level3}){match3.group(2)}'
            new_lines.append(new_line)
            continue

        # No match, keep line as is
        new_lines.append(line)

    return '\n'.join(new_lines)


def renumber_paragraphs(content: str) -> Tuple[str, int]:
    """
    Renumber paragraph numbers sequentially.

    Pattern: (N) at the start of a line followed by &emsp; or whitespace
    Returns: (new_content, paragraph_count)
    """
    # Pattern: standalone paragraph number like (42) or (1)
    # Must be at start of line, followed by &emsp; or whitespace
    pattern = r'^(\()(\d+)(\)(&emsp;|\s))'

    lines = content.split('\n')
    new_lines = []
    para_count = 0

    for line in lines:
        # Check if line starts with a paragraph number
        match = re.match(pattern, line)
        if match:
            para_count += 1
            # Keep the separator (&emsp; or space) after the number
            separator = match.group(4)
            rest_of_line = line[match.end():]
            new_line = f'({para_count}){separator}{rest_of_line}'
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines), para_count


def update_front_matter_count(content: str, para_count: int) -> str:
    """Update the paragraph_count field in front matter."""
    pattern = r'^(paragraph_count:\s*)\d+(.*)$'
    return re.sub(pattern, f'\\g<1>{para_count}\\2', content, flags=re.MULTILINE)


def renumber(input_file: str) -> None:
    """Main renumbering function."""
    content = Path(input_file).read_text(encoding='utf-8')

    # Step 1: Remove draft sections temporarily
    content, drafts = remove_draft_sections(content)

    # Step 2: Renumber sections
    content = renumber_sections(content)

    # Step 3: Renumber paragraphs
    content, para_count = renumber_paragraphs(content)

    # Step 4: Update paragraph count in front matter
    content = update_front_matter_count(content, para_count)

    # Step 5: Restore draft sections
    content = restore_draft_sections(content, drafts)

    # Write the result
    Path(input_file).write_text(content, encoding='utf-8')

    print(f"Renumbering complete:")
    print(f"  - Sections renumbered")
    print(f"  - Paragraphs renumbered: {para_count} total")
    print(f"  - Front matter updated: paragraph_count = {para_count}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 renumber.py <input_file>")
        print("Example: python3 renumber.py index.en.md")
        sys.exit(1)

    renumber(sys.argv[1])
