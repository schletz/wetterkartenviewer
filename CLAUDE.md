# Wetterkartenviewer

## Dokumentation

- Vor Änderungen an `scripts/`: `REFERENCE.scripts.md` lesen.
- Vor Änderungen an `src/` (App): `REFERENCE.webapp.md` lesen.
- Vor Änderungen an `api/` (Azure Function): `REFERENCE.api.md` lesen.
- `REFERENCE.md` ist das Inhaltsverzeichnis.
- Die Referenzen beschreiben Aufbau, Datenfluss, Verträge, Konstanten, Erweiterungspunkte und Fallstricke. Quellcode daher nur gezielt nachlesen.
- Ändert sich etwas, das in der Referenz beschrieben ist: Referenz samt Diagrammen im selben Arbeitsgang nachziehen. Dafür den Skill `document-software` laden.

## Rechner

| Rechner | System | Aufgabe |
|---|---|---|
| Server | Mac | Führt `download_loop.sh` aus. Holt alle 10 Minuten die neuesten Vorhersagedaten (sofern vorhanden). |
| Dev-PC | Windows | Entwicklung |

## Commits

Nach Repo-Änderung und Freigabe durch den User der Reihe nach:

1. `commit`
2. `git pull --rebase`
3. `git push`

Der Push löst den github Workflow aus. Dieser überträgt reine Codeänderungen an die Live App: https://schletz.github.io/wetterkartenviewer

## Manuelles Deployment

- Bei neuen Prognosedaten rendert und veröffentlicht das Downloadskript gemäß Manifest neue Karten.
- Ziel bei neuen Features: nicht die gesamte Pipeline mit `download_data_with_reset.sh --force` am Server durchlaufen.

Vorgehen:

1. Der Dev-PC-Agent kommuniziert mit dem Agent am Server (Remote Session in Claude).
2. Der Server holt den neuen Code: `git fetch && git reset --hard origin/main`.
3. Der Server führt gezielt nur die für das Deployment nötigen Pipeline-Teile aus.

**Fallstrick (Server):** Der Commit des Dev-PCs löst bereits den github Workflow aus. Macht der Server kurz danach ebenfalls einen commit, wird der vorige Workflow abgebrochen. Der Server muss daher prüfen, ob gerade ein Workflow läuft.

**Doppelte Deployments vermeiden:** Braucht eine Codeänderung neue Daten vom Server (z. B. ein neues Feld in einer Serien-JSON), committet der Dev-PC mit `[skip ci]` in der Commit-Nachricht. Der Push startet dann keinen Workflow, und der App-Code geht erst mit dem Deployment des Servers live, zusammen mit den passenden Daten. Der Server deployt nach seinem `publish_maps.py`:

- Hat `publish_maps.py` ein geändertes Manifest gepusht, startet dieser Push den Workflow.
- Sonst (Manifest unverändert, kein Commit) startet der Server den Workflow per Hand: `gh workflow run deploy.yml`.

**Fallstrick (Serien-JSON im selben Lauf):** `point_series.py` schreibt eine Datei nur, wenn sich ihre Version (der Lauf) ändert. Für ein neues Feld im laufenden Lauf muss der Server die Datei in `maps/austria/` vorher löschen. Die Version bleibt dabei gleich, daher kann ein Browser mit der alten Datei im Cache sie bis zum nächsten Lauf weiter zeigen.
