"""The subset of Markdown that the analysis uses, converted to HTML blocks."""

import re
from html import escape


class MarkdownHtml:
    """Converts "#" to "###" headings, paragraphs, "- " lists and **bold** / *italic*."""

    @staticmethod
    def inline(text: str) -> str:
        """Escape HTML and convert **bold** and *italic*."""
        text = escape(text, quote=False)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)

    def blocks(self, markdown: str) -> tuple[list[str], str]:
        """Convert the Markdown into a list of HTML blocks.

        Returns:
            The blocks and the text of the first "#" heading (or "").
        """
        blocks, paragraph, items, title = [], [], [], ""

        def flush():
            if paragraph:
                blocks.append(f"<p>{self.inline(' '.join(paragraph))}</p>")
                paragraph.clear()
            if items:
                blocks.append("<ul>" + "".join(f"<li>{self.inline(item)}</li>" for item in items) + "</ul>")
                items.clear()

        for line in markdown.splitlines():
            stripped = line.strip()
            heading = re.match(r"(#{1,3})\s+(.*)", stripped)
            if heading:
                flush()
                level = len(heading.group(1))
                title = title or (heading.group(2) if level == 1 else "")
                blocks.append(f"<h{level}>{self.inline(heading.group(2))}</h{level}>")
            elif stripped.startswith("- "):
                if paragraph:
                    flush()
                items.append(stripped[2:])
            elif not stripped:
                flush()
            elif items:
                items[-1] += " " + stripped  # continuation line of a list item
            else:
                paragraph.append(stripped)
        flush()
        return blocks, title
