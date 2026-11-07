# Wetterkartenviewer

## Dokumentation

- Vor Änderungen an `scripts/`: `REFERENCE.scripts.md` lesen.
- Vor Änderungen an `src/` (App): `REFERENCE.webapp.md` lesen.
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
