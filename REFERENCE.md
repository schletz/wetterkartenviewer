# wetterkartenviewer — agent reference

The repository holds three products; read the reference of the one you work on.

| File | Product | Contents |
| --- | --- | --- |
| [REFERENCE.scripts.md](REFERENCE.scripts.md) | Python data pipeline in `scripts/` | download of ECMWF IFS and ICON-D2, derived fields, chart rendering, tile videos, publishing; diagrams `pipeline`, `update_maps`, `download`, `grib`, `render`; file formats, contract with the skill synop |
| [REFERENCE.webapp.md](REFERENCE.webapp.md) | React app in `src/` | start page with meteograms, map page with tiles and step slider; diagram `app`; manifest as the app reads it, viewer config |
| [skills/synop/scripts/REFERENCE.md](skills/synop/scripts/REFERENCE.md) | Skill synop in `skills/synop` | reads `data/` or its blob mirror (`fetch_data.py`), location tables, marked charts, HTML report; `SKILL.md` is the agent's workflow, `references/html_report.md` its report steps |

Both meet in `maps/manifest.json` (written by the pipeline, read by the app) and `src/config/viewer.config.json` (tile layers, read by both).
Rendered diagrams for people are in `docs/`.
