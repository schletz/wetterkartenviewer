/* jshint strict:global */
/* globals document */

"use strict";

/**
 * Renders the in-band legend data of the ECMWF Open-Charts packages API as a DOM element.
 * Unterstützt wird der Legendentyp "colorbar" (Farbskala mit Wertebereichen). Andere Typen
 * wie "double-line" werden ignoriert, da sie nur Linienstile beschreiben.
 */
var EcmwfChartLegend = {
    /**
     * Creates one legend element containing all colorbars of the passed legend array.
     *
     * @param {Array} legend Das legend-Array aus results[validTime].legend der API-Antwort.
     * @returns {HTMLElement|null} Das Legendenelement oder null, wenn keine colorbar
     * enthalten ist.
     */
    createElement: function (legend) {
        if (!Array.isArray(legend)) { return null; }
        var self = this;
        var container = null;
        legend.forEach(function (item) {
            if (!item || !item.data || item.data.type !== "colorbar") { return; }
            if (container === null) {
                container = document.createElement("div");
                container.className = "chartLegend";
            }
            container.appendChild(self.createColorbar(item.data));
        });
        return container;
    },

    /**
     * Creates the title line, the boundary labels and the colored cell strip for one
     * colorbar dataset. Die Werte sind Bereichsgrenzen und werden deshalb – wie im
     * ECMWF-Original – mittig über den Zellgrenzen platziert, nicht in den Zellen.
     *
     * @param {object} data Colorbar-Daten mit title und entries[{min-range, max-range, colour}].
     * @returns {HTMLElement}
     */
    createColorbar: function (data) {
        var colorbar = document.createElement("div");
        var entries = data.entries || [];

        if (data.title) {
            var title = document.createElement("div");
            title.className = "chartLegendTitle";
            title.appendChild(document.createTextNode(data.title));
            colorbar.appendChild(title);
        }

        var labels = document.createElement("div");
        labels.className = "chartLegendLabels";
        entries.forEach(function (entry, i) {
            // Pro Zelle ein gleich breites Div; die Labels sitzen absolut auf dessen Rändern.
            var cell = document.createElement("div");
            // Der linke Rand der ersten Zelle ist ebenfalls eine Bereichsgrenze.
            if (i === 0 && entry["min-range"] !== undefined) {
                cell.appendChild(EcmwfChartLegend.createLabel(entry["min-range"], "chartLegendLabelFirst"));
            }
            if (entry["max-range"] !== undefined) {
                // Das letzte Label darf nicht über den rechten Rand hinausragen.
                cell.appendChild(EcmwfChartLegend.createLabel(entry["max-range"],
                    i === entries.length - 1 ? "chartLegendLabelLast" : ""));
            }
            labels.appendChild(cell);
        });
        colorbar.appendChild(labels);

        var bar = document.createElement("div");
        bar.className = "chartLegendBar";
        entries.forEach(function (entry) {
            var cell = document.createElement("div");
            // Das colour-Feld ("RGBA(r,g,b,a)") ist direkt als CSS-Farbe verwendbar.
            cell.style.backgroundColor = entry.colour;
            bar.appendChild(cell);
        });
        colorbar.appendChild(bar);
        return colorbar;
    },

    /**
     * Creates one boundary label span.
     *
     * @param {string} value Der Grenzwert.
     * @param {string} modifier Zusätzliche CSS-Klasse für Rand-Labels oder "".
     * @returns {HTMLElement}
     */
    createLabel: function (value, modifier) {
        var label = document.createElement("span");
        label.className = modifier ? "chartLegendLabel " + modifier : "chartLegendLabel";
        label.appendChild(document.createTextNode(value));
        return label;
    }
};
