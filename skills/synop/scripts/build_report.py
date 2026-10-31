"""Assemble the analysis, the diagram and the data into one HTML file.

The analysis is written as Markdown by the agent; only the subset that
the analysis uses is converted (lib/markdown_html.py). The SVG diagram is
embedded inline after the overview, i.e. before the first "##" heading,
so the reader sees the course of the air mass before the day by day
text. The TSV becomes a collapsible table, which also serves readers who
cannot use the diagram.

The result is a single self-contained file without external resources.
"""

import argparse
import sys
from html import escape
from pathlib import Path

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.forecast_tsv import ForecastTsv  # noqa: E402
from lib.markdown_html import MarkdownHtml  # noqa: E402

STYLE = """
:root { color-scheme: light dark; --bg:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --rule:#e3e2de; }
@media (prefers-color-scheme: dark) { :root { --bg:#1a1a19; --ink:#f0efec; --ink-2:#c3c2b7; --rule:#33322f; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 64rem; margin: 0 auto; padding: 2rem 16px 4rem; }
h1 { font-size: 1.6rem; line-height: 1.25; margin: 0 0 1rem; }
h2 { font-size: 1.2rem; margin: 2.2rem 0 .4rem; padding-top: 1rem; border-top: 1px solid var(--rule); }
h3 { font-size: 1rem; margin: 1.4rem 0 .3rem; }
p, ul { margin: 0 0 .9rem; }
/* The paragraph right below the title is the plain language summary for end users. */
h1 + p { font-size: 1.125rem; padding: .8rem 1rem; border-left: 4px solid var(--rule);
  background: color-mix(in srgb, var(--rule) 35%, transparent); }
figure { margin: 1.5rem 0 2rem; }
figure svg { display: block; width: 100%; height: auto; }
figcaption, details { color: var(--ink-2); font-size: .875rem; }
details { margin-top: .6rem; }
summary { cursor: pointer; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; font-variant-numeric: tabular-nums; margin-top: .6rem; }
th, td { padding: .2rem .7rem; border-bottom: 1px solid var(--rule); text-align: right; white-space: nowrap; }
th:first-child, td:first-child, th:last-child, td:last-child { text-align: left; }
"""


def data_table(tsv: ForecastTsv, summary):
    """Render the TSV of location_table.py as a collapsible table.

    The column heads are symbols, so only the summary line depends on the
    language of the report.
    """
    def number(value, digits):
        return f"{value:.{digits}f}" if value is not None else ""

    rows = []
    for valid, step, t850, thickness, rh700 in tsv.air_mass():
        cells = [f"{valid:%d.%m. %H} UTC", f"+{step} h" if step is not None else "",
                 number(t850, 1), number(thickness, 1), number(rh700, 0)]
        rows.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr>")
    head = "".join(f"<th>{name}</th>" for name in
                   ("UTC", "T+", "T850 °C", "Z1000–500 dam", "RH700 %"))
    return (f'<details><summary>{escape(summary)}</summary><div class="table-wrap"><table>'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody>"
            "</table></div></details>")


def build_figure(svg, caption, table):
    """Wrap the inline SVG, its caption and the data table in a figure."""
    return (f"<figure>{svg.strip()}"
            + (f"<figcaption>{MarkdownHtml.inline(caption)}</figcaption>" if caption else "")
            + table + "</figure>")


def build_html(blocks, title, figure, lang):
    """Put the figure before the first "##" heading and wrap the page."""
    split = next((i for i, block in enumerate(blocks) if block.startswith("<h2")), len(blocks))
    body = blocks[:split] + [figure] + blocks[split:]
    return (f'<!doctype html>\n<html lang="{escape(lang)}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{escape(title or 'Synoptic analysis')}</title>\n<style>{STYLE}</style>\n"
            "</head>\n<body>\n<main>\n" + "\n".join(body) + "\n</main>\n</body>\n</html>\n")


def main(argv):
    """Parse the arguments and write the HTML file."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--markdown", required=True, help="analysis in Markdown")
    parser.add_argument("--svg", required=True, help="diagram written by generate_diagram.py")
    parser.add_argument("--tsv", help="data of location_table.py --tsv, shown as table")
    parser.add_argument("--caption", default="", help="caption below the diagram")
    parser.add_argument("--table-summary", default="Data", help="label of the collapsible data table")
    parser.add_argument("--lang", default="de", help="language of the analysis (HTML lang attribute)")
    parser.add_argument("--out", required=True, help="HTML file to write")
    args = parser.parse_args(argv)

    try:
        markdown = Path(args.markdown).read_text(encoding="utf-8")
        svg = Path(args.svg).read_text(encoding="utf-8")
        table = data_table(ForecastTsv(args.tsv), args.table_summary) if args.tsv else ""
    except (OSError, ValueError, KeyError) as error:
        print(f"Cannot read input: {error}", file=sys.stderr)
        return 1

    blocks, title = MarkdownHtml().blocks(markdown)
    html = build_html(blocks, title, build_figure(svg, args.caption, table), args.lang)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Report written to {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
