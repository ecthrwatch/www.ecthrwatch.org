#!/usr/bin/env python3
"""
Preprocess index.en.md for PDF generation via Pandoc.
Strips Hugo-specific syntax and prepares for LaTeX conversion.

Usage:
    python preprocess_for_pdf.py <input.md> <output.md> [OPTIONS]

Options:
    --green-color=COLOR     LaTeX color name for green text (default: ForestGreen)
    --red-color=COLOR       LaTeX color name for red text (default: red)
    --para-num-size=SIZE    Font size for paragraph numbers (default: normalsize)
"""

import argparse
import re
import sys
from pathlib import Path
from html.parser import HTMLParser


class HTMLTableToMarkdown(HTMLParser):
    """Convert HTML tables to Markdown format."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_thead = False
        self.in_tbody = False
        self.in_row = False
        self.in_cell = False
        self.is_header = False
        self.current_row = []
        self.rows = []
        self.header_row = []
        self.cell_content = ""

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.rows = []
            self.header_row = []
        elif tag == 'thead':
            self.in_thead = True
        elif tag == 'tbody':
            self.in_tbody = True
        elif tag == 'tr':
            self.in_row = True
            self.current_row = []
        elif tag in ('th', 'td'):
            self.in_cell = True
            self.is_header = (tag == 'th') or self.in_thead
            self.cell_content = ""

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'thead':
            self.in_thead = False
        elif tag == 'tbody':
            self.in_tbody = False
        elif tag == 'tr':
            self.in_row = False
            if self.header_row == [] and self.current_row:
                self.header_row = self.current_row
            else:
                self.rows.append(self.current_row)
            self.current_row = []
        elif tag in ('th', 'td'):
            self.in_cell = False
            content = self.cell_content.strip()
            content = re.sub(r'\\textcolor\{[^}]+\}\{([^}]+)\}', r'\1', content)
            content = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', content)
            content = re.sub(r'\\textit\{([^}]+)\}', r'*\1*', content)
            content = re.sub(r'\\underline\{([^}]+)\}', r'\1', content)
            self.current_row.append(content)
            self.cell_content = ""

    def handle_data(self, data):
        if self.in_cell:
            self.cell_content += data

    def get_markdown(self):
        """Generate Markdown table from parsed data."""
        if not self.header_row and not self.rows:
            return ""

        header = self.header_row if self.header_row else (self.rows[0] if self.rows else [])
        data_rows = self.rows if self.header_row else self.rows[1:]

        if not header:
            return ""

        lines = []
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        for row in data_rows:
            while len(row) < len(header):
                row.append("")
            lines.append("| " + " | ".join(row[:len(header)]) + " |")

        return "\n".join(lines)


def convert_html_table_to_markdown(table_html):
    """Convert an HTML table to Markdown format."""
    parser = HTMLTableToMarkdown()
    try:
        parser.feed(table_html)
        return parser.get_markdown()
    except Exception:
        return table_html


def preprocess(input_file: str, output_file: str, green_color: str = "ForestGreen",
               red_color: str = "red", para_num_size: str = "normalsize"):
    """Preprocess markdown for PDF generation."""
    content = Path(input_file).read_text(encoding='utf-8')

    # 0. Version info is now only in front matter and header/footer notices
    # No need to replace version#initial in paragraph numbers anymore

    # 1. Remove Hugo frontmatter (YAML between --- markers)
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # 2. Remove <style> blocks
    content = re.sub(r'<style>.*?</style>', '', content, flags=re.DOTALL)

    # 3. Remove manual-toc div (we'll use Pandoc's TOC instead)
    content = re.sub(r'<div class="manual-toc"[^>]*>.*?</div>\s*</div>', '', content, flags=re.DOTALL)

    # 4. Convert Hugo imgproc2 shortcodes to standard markdown images
    def convert_imgproc(match):
        shortcode = match.group(0)
        name_match = re.search(r'name="([^"]+)"', shortcode)
        alt_match = re.search(r'alt="([^"]*)"', shortcode)

        if name_match:
            name = name_match.group(1)
            alt = alt_match.group(1) if alt_match else ""
        else:
            format1_match = re.search(r'imgproc2\s+([^\s"]+)', shortcode)
            if format1_match:
                name = format1_match.group(1)
            else:
                name = "image"
            alt = ""

        if not name.startswith('images/') and not name.startswith('/'):
            name = f'images/{name}'

        return f'![{alt}]({name})'

    content = re.sub(r'\{\{<\s*imgproc2[^>]*/?>\}\}', convert_imgproc, content)

    # 5. Remove remaining Hugo shortcodes
    content = re.sub(r'\{\{<[^>]*>\}\}', '', content)

    # 6. Convert &emsp; to regular spaces
    content = content.replace('&emsp;', ' ')

    # 7. Convert Hugo/MathJax inline math delimiters to Pandoc format
    content = re.sub(r'\\\\[(](.+?)\\\\[)]', r'$\1$', content)

    # 7b. Fix escaped brackets
    content = re.sub(r'\\\\?\[([^\]]+)\\\\?\]', r'[\1]', content)

    # 8. Handle spans with class attribute (like double-strike)
    content = re.sub(r'<span class="double-strike">([^<]*)</span>', r'\1', content)

    # 9. Convert HTML tables to Markdown tables BEFORE processing spans
    def replace_table(match):
        table_html = match.group(0)
        return "\n\n" + convert_html_table_to_markdown(table_html) + "\n\n"

    content = re.sub(r'<table>.*?</table>', replace_table, content, flags=re.DOTALL)

    # 10. Convert HTML span styles to LaTeX commands for PDF rendering
    def convert_span_style(match):
        style = match.group(1)
        text = match.group(2)

        # Escape special LaTeX characters in the text BEFORE wrapping in commands
        text = text.replace('&', r'\&')
        text = text.replace('#', r'\#')
        text = text.replace('%', r'\%')

        result = text
        has_underline = 'text-decoration:underline' in style or 'text-decoration: underline' in style

        # Check for color first - we need to know if there's a color
        color_match = re.search(r'color:\s*([^;"\s]+)', style)
        color = None
        if color_match:
            color = color_match.group(1).lower()
            # Map standard colors to configurable ones
            if color in ('green', '#00ff00', '#008000'):
                color = green_color
            elif color in ('red', '#ff0000'):
                color = red_color
            else:
                color = color_match.group(1)

        # Check for bold (apply to text)
        if 'font-weight:bold' in style or 'font-weight: bold' in style:
            result = f'\\textbf{{{result}}}'

        # Check for italic
        if 'font-style:italic' in style or 'font-style: italic' in style:
            result = f'\\textit{{{result}}}'

        # Apply color
        if color:
            result = f'\\textcolor{{{color}}}{{{result}}}'

        # Apply underline only if there's NO color (ulem's \uline works with bold/italic but not with \textcolor)
        # When color is present, the color itself provides sufficient emphasis
        if has_underline and not color:
            result = f'\\uline{{{result}}}'

        return result

    # Process nested spans from innermost to outermost
    for _ in range(5):
        content = re.sub(
            r'<span\s+style="([^"]+)"[^>]*>([^<]*(?:<(?!/span>)[^<]*)*)</span>',
            convert_span_style,
            content
        )

    # 11. Remove any remaining span tags (without style)
    content = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', content)

    # 12. Convert other HTML entities
    content = content.replace('&nbsp;', '~')  # Non-breaking space in LaTeX
    content = content.replace('&mdash;', '—')
    content = content.replace('&ndash;', '–')
    content = content.replace('&euro;', '€')
    content = content.replace('&pound;', '£')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')
    content = content.replace('&amp;', '&')

    # 13. Remove HTML id attributes from headers
    content = re.sub(r'\s*\{id="[^"]*"\}', '', content)

    # 14. Format paragraph numbers with configurable size
    # (N) at start of line -> raw LaTeX block with size command
    def format_para_num(match):
        number = match.group(1)  # Just the number (without parentheses)
        # Use Pandoc raw LaTeX inline syntax: `\command`{=latex}
        return f'`{{\\{para_num_size} ({number})}}`{{=latex}} '

    # Match (N) at the start of a line followed by space (paragraph number format)
    # Capture just the number, not the parentheses
    content = re.sub(r'^\((\d+)\) ', format_para_num, content, flags=re.MULTILINE)

    # 15. Make email addresses non-breaking (use \mbox{})
    # Match common email patterns
    def protect_email(match):
        email = match.group(0)
        # Use Pandoc raw LaTeX inline syntax
        return f'`\\mbox{{{email}}}`{{=latex}}'

    content = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', protect_email, content)

    # 16. Convert footnote definition URLs to use \url{} for proper line breaking
    # Footnote format: [^name]: https://...
    # This ensures the entire URL is clickable even when it breaks across lines
    def convert_footnote_url(match):
        footnote_name = match.group(1)
        url = match.group(2)
        # Use raw LaTeX \url{} which handles line breaks properly
        return f'[^{footnote_name}]: `\\url{{{url}}}`{{=latex}}'

    content = re.sub(
        r'\[\^([^\]]+)\]:\s*(https?://[^\s]+)',
        convert_footnote_url,
        content
    )

    # 17. Clean up multiple blank lines
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    # 18. Handle <br> tags
    content = content.replace('<br>', '\n')
    content = content.replace('<br/>', '\n')
    content = content.replace('<br />', '\n')

    Path(output_file).write_text(content, encoding='utf-8')
    print(f"Preprocessed: {input_file} -> {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess markdown for PDF generation via Pandoc'
    )
    parser.add_argument('input_file', help='Input markdown file')
    parser.add_argument('output_file', help='Output preprocessed file')
    parser.add_argument('--green-color', default='ForestGreen',
                        help='LaTeX color name for green text (default: ForestGreen)')
    parser.add_argument('--red-color', default='red',
                        help='LaTeX color name for red text (default: red)')
    parser.add_argument('--para-num-size', default='normalsize',
                        help='Font size for paragraph numbers (default: normalsize)')

    args = parser.parse_args()

    preprocess(
        args.input_file,
        args.output_file,
        green_color=args.green_color,
        red_color=args.red_color,
        para_num_size=args.para_num_size
    )


if __name__ == "__main__":
    main()
