/* jshint strict:global */
/* globals document */

"use strict";

/**
 * Renders the run metadata of the ECMWF Open-Charts packages API as a header line
 * showing the model run (base_time) and the valid time of the chart.
 */
var EcmwfChartHeader = {
    /**
     * Creates the header element for one chart.
     *
     * @param {object} values Das values-Objekt aus results[validTime].values der API-Antwort
     * mit request{base_time, valid_time, step}.
     * @returns {HTMLElement|null} Das Kopfzeilenelement oder null bei fehlenden Daten.
     */
    createElement: function (values) {
        var request = values && values.request ? values.request : null;
        if (request === null) { return null; }

        var baseTime = this.parseCompactTime(request.base_time);
        var validTime = this.parseCompactTime(request.valid_time);
        if (baseTime === null || validTime === null) { return null; }

        var header = document.createElement("div");
        header.className = "chartHeader";
        header.appendChild(this.createPart("Lauf: " + baseTime.getGermanStr(true)));
        header.appendChild(this.createPart("Gültig: " + validTime.getGermanStr(true) +
            (isNaN(request.step) ? "" : " (+" + request.step + " h)")));
        return header;
    },

    /**
     * Creates one text span of the header line.
     *
     * @param {string} text
     * @returns {HTMLElement}
     */
    createPart: function (text) {
        var part = document.createElement("span");
        part.appendChild(document.createTextNode(text));
        return part;
    },

    /**
     * Parses the compact UTC time format of the packages API.
     *
     * @param {string} value Zeitstring der Form YYYYMMDDHHMM, z. B. "202607101200".
     * @returns {Date|null} Das Datumsobjekt oder null bei ungültigem String.
     */
    parseCompactTime: function (value) {
        if (typeof value !== "string" || !/^\d{12}$/.test(value)) { return null; }
        var d = new Date(0);
        d.setUTCFullYear(parseInt(value.slice(0, 4), 10));
        d.setUTCMonth(parseInt(value.slice(4, 6), 10) - 1);
        d.setUTCDate(parseInt(value.slice(6, 8), 10));
        d.setUTCHours(parseInt(value.slice(8, 10), 10));
        d.setUTCMinutes(parseInt(value.slice(10, 12), 10));
        return d;
    }
};
