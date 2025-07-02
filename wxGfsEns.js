/* jshint strict:global */
/* globals $, Image, window, console */
"use strict";

/* 
 * DATE Erweiterungen 
 */
Date.fromUnixTimestamp = function (timestamp) {
    var d = new Date(timestamp * 1000);
    return d;
};
Date.prototype.getUnixTimestamp = function () {
    return this.getTime() / 1000;
};
Date.prototype.getIsoDate = function () {
    var month = this.getUTCMonth() + 1;
    var day = this.getUTCDate();
    var hour = this.getUTCHours();
    return "" + this.getUTCFullYear() + "-" +
        (month < 10 ? "0" : "") + month + "-" +
        (day < 10 ? "0" : "") + day + " " +
        (hour < 10 ? "0" : "") + hour + "Z";
};

/*
 * GfsEns Object
 */

var GfsEns = {
    parsedData: {},
    /* Der Startzeitpunkt der Diagrammausgabe ist die letzte volle 6. Stunde, die aber mindestens 
     * 6 Stunden her ist. Wird in den getData Methoden verwendet. */
    startDate: new Date(Math.floor((Date.now() - 6 * 3600e3) / 6 / 3600e3) * 6 * 3600e3).getTime(),
    runsLoaded: 0,    // Für die Bestimmung, dann alle Ajax Requests fertig sind.
    windColors: [[0, '#CCCCCC'], [10, '#6E79FA'], [20, '#1AFF00'], [30, '#FFE900'], [40, '#FF0000'], [50, '#CC0074']],
    windSectors: ["N", "NO", "O", "SO", "S", "SW", "W", "NW", "N"],
    onReady: function (source) { return; },
    onError: function (source, message) { return; },
    onLoaded: function (source, site, run, count, lastTime) { return; },
    /**
     * Lädt die Wetterdaten von wxcharts und meteociel. Dabei wird ein CORS Proxy benötigt, da der
     * Server natürlich kein Allow origin * im Header sendet.
     * Von Wxcharts kann unter der URL http://wxcharts.eu/php/get_gefs.php?lat=48.0&lon=16.5&database=(00,06,12,18)
     * der Modelloutput T2m, T850hpa, Precipiation, U und V 10m Windkomponenten und SLP als JSON
     * geladen werden.
     * Meteociel stellt unter http://www.meteociel.fr/modeles/gefs_table.php?lat=48&lon=16.5&run=(0,6,12,18)&mode=1
     * eine Tabelle mit den Daten für die übergebenen Koordindaten bereit.
     * Als Koordinaten sind 48° NB und 16.5° ÖL fix in der URL.
     * 
     */
    loadData: function () {
        var self = this;
        /* WXCHARTS Daten (JSON) laden. */
        ["00", "06", "12", "18"].forEach(function (runParam) {
            var url = "http://wxcharts.eu/php/get_gefs.php?lat=48.0&lon=16.5&database=" + runParam;
            $.ajax({ url: url, dataType: "json" }).done(function (data) {
                self.runsLoaded++;
                self.parseData(data);
                /* Wenn alle 8 Abfragen gemacht wurden, wird dieses Event aufgerufen. */
                if (self.runsLoaded == 8) {
                    self.onReady(self);
                }
            }).fail(function () {
                self.onError(self, "REQUEST_FAILED", url);
            });
        });
        /* Meteociel Tabelle laden (HTML) */
        ["0", "6", "12", "18"].forEach(function (runParam) {
            var url = "http://www.meteociel.fr/modeles/gefs_table.php?lat=48&lon=16.5&run=" + runParam + "&mode=1";
            $.ajax({ url: url, dataType: "html" }).done(function (data) {
                self.runsLoaded++;
                self.parseMeteocielData(data, "TMP_500");
                if (self.runsLoaded == 8) {
                    self.onReady(self);
                }
            }).fail(function () {
                self.onError(self, "REQUEST_FAILED", url);
            });
        });
    },

    /**
     * Liest das JSON Array von Wxcharts ein und schreibt das Ergebnis in parsedData.
     * 
     * @param {object} data Die JSON Daten von Wxcharts.
     */
    parseData: function (data) {
        var self = this;
        try {
            /* Gelesenen GFS Hauptlauf verarbeiten. Das ist der 23. (Index 22) im JSON Array. */
            var run = 1 * data[22][0]["UNIX_TIMESTAMP(vt)"];
            var lastTime = 0;                                         // Der letzte Vorhersagezeitpunkt.
            /* Der GFS Hauptlauf ist in ein Array von Vorhersagezeitpunkten unterteilt, die alle
             * Modellparameter beinhalten. */
            data[22].forEach(function (timeData) {
                var time = 1 * timeData["UNIX_TIMESTAMP(vt)"];
                lastTime = Math.max(lastTime, time);
                /* Alle Parameter durchgehen und diesen Wert in unser parsedData Objekt einhängen. */
                for (var param in timeData) {
                    self.appendData(param, run, time, timeData[param]);
                }
            });

            /* Die 30 Jahres Mittelwerte von Index 23 lesen. */
            data[23].forEach(function (timeData) {
                var time = 1 * timeData["UNIX_TIMESTAMP(vt)"];
                for (var param in timeData) {
                    self.appendData(param + "_30YR", run, time, timeData[param]);
                }
            });
            self.onLoaded(self, "Wxcharts", Date.fromUnixTimestamp(run), data[22].length, Date.fromUnixTimestamp(lastTime));
        }
        catch (e) {
            self.onError(self, "WXPARSE_FAILED");
            return false;
        }
        return true;

    },

    /**
     * Liest die HTML Seite der Tabellenausgabe von Meteociel.
     * 
     * @param {string} data Der HTML String.
     * @param {string} param Welcher Parameter angefordert wurde (z. B. TMP_500). Wird dann bei
     * getData verwendet.
     * @returns 
     */
    parseMeteocielData: function (data, param) {
        try {
            /* RegExp für die einzelne Datenzeile. Sie beginnt mit dem Datum, die letzte Zelle ist
             * der Wert des GFS Hauptlaufes. Davor sind die Ensembles. */
            var colRe = /<tr><td.*?>(Date|(\d+)-(\d+)-(\d+) (\d+)Z)<\/td>.*?<td.*?>([0-9\-\+\.]+|GFS)(<\/font>)?<\/td><\/tr>/ig;
            var col = null;
            var headerOk = false;
            var time = null;
            var run = 0;
            var count = 0;

            /* Die Datentabelle raussuchen. */
            var table = /<table class='gefs'>(.*?)<\/table>/i.exec(data);
            if (table === null) { return; }
            /* Durch jede Datenzeile durchgehen. */
            while ((col = colRe.exec(table[1])) !== null) {
                /* Nur wenn in der Kopfzeile das Wort Date und GFS steht, dann ist der Tabellenaufbau
                 * wie erwartet. Sonst werden u. U. Ensembles mit dem Hauptlauf verwechselt! */
                if (col[1] == "Date" && col[6] == "GFS") {
                    headerOk = true;
                }
                else {
                    if (headerOk) {
                        time = new Date(Date.UTC(col[2], col[3] - 1, col[4], col[5], 0, 0)).getUnixTimestamp();
                        /* Der 1. Datensatz bestimmt den Lauf. */
                        if (run === 0) { run = time; }
                        this.appendData(param, run, time, col[6]);
                        count++;
                    }
                }
            }
            this.onLoaded(this, "Meteociel", Date.fromUnixTimestamp(run), count, Date.fromUnixTimestamp(time));
        }
        catch (e) {
            this.onError(this, "METEOCIELPARSE_FAILED");
            return false;
        }
        return true;
    },

    /**
     * Hängt einen Parameterwert (z. B. T2m = 2.1°C) in parsedData ein. Dabei kann der selbe
     * Parameterwert und der gleiche Zeitpunkt mehrmals vorkommen, da er von unterschiedlichen
     * Läufen stammt. Hier werden die Daten zu minValue und maxValue aggregiert. Der neueste
     * Wert wird in val geschrieben.
     * @param {string} param Der Parametername (z. B. TMP_2).
     * @param {number} run Der UNIX Timestamp des Laufes. Dadurch wird heraufgefundne, welcher
     * Wert der Letzte ist und in val geschrieben wird.
     * @param {number} time Der UNIX Timestamp des vorhergesagten Zeitpunktes.
     * @param {any} val Der Messwert.
     */
    appendData: function (param, run, time, val) {
        if (val === undefined || val === null || val === "null") { return false; }
        try {
            if (this.parsedData[param] === undefined) { this.parsedData[param] = []; }
            if (this.parsedData[param][time] === undefined) {
                this.parsedData[param][time] = {
                    /* Die Grundstruktur anlegen. */
                    /* Zeitpunkt des letzten (neuesten) Laufes, dieser Lauf wird in val geschriebem. */
                    lastRun: Date.fromUnixTimestamp(0),
                    /* Der vorhergesagte Zeitpunkt. */
                    time: Date.fromUnixTimestamp(time),
                    /* Der Messwert. */
                    val: -999,
                    /* Der kleinste Wert, der bei allen bearbeiteten Läufen für diesen Zeitpunkt auf-
                     * getreten ist. */
                    minVal: Number.MAX_VALUE,
                    maxVal: -1 * Number.MAX_VALUE,
                    /* Die Anzahl der Läufe, die diesen Wert berechneten. */
                    count: 0
                };
            }
            var parsedDataTime = this.parsedData[param][time];
            if (!isNaN(val))
                val *= 1;

            /* Wenn der Lauf neuer ist, ist dies der neue aktuelle Wert. */
            if (parsedDataTime.lastRun.getUnixTimestamp() < run) {
                parsedDataTime.val = val;
                parsedDataTime.lastRun = Date.fromUnixTimestamp(run);
            }
            parsedDataTime.minVal = Math.min(parsedDataTime.minVal, val);
            parsedDataTime.maxVal = Math.max(parsedDataTime.maxVal, val);
            parsedDataTime.count++;
        }
        catch (e) {
            this.onError(this, "DATA_APPEND_FAILED");
            return false;
        }
        return true;
    },


    /**
     * Liefert ein JSON Objekt, welches eine Zeitreihe für den Parameter zurückgibt (values) oder
     * die Min und Max Werte der Läufe (Property ranges).
     * @example var dataSource = getData("TMP_2").ranges;
     * 
     * @param {string} param Der Parametername. TMP_2 wenn nicht übergeben wird.
     * @returns Ein JSON Objekt mit dem Aufbau
     * {values: [[Timestamp, Value], ...], ranges: [[Timestamp, Min, Max], ...]}
     */
    getData: function (param) {
        if (param === undefined) { param = "TMP_2"; }
        var data = this.parsedData[param];
        if (data === undefined) { return []; }

        var timeData = null;
        var result = { values: [], ranges: [] };
        /* Ein forEach würde sehr lange brauchen, da die UNIX Timestamps die Array Inizes sind.
         * Dies ist die schnellste Möglichkeit, ein sparse Array zu iterieren. */
        for (var time in data) {
            timeData = data[time];
            /* Nur wenn der Zeitpunkt im Intervall [jetzt-6h, letzterLauf + 240h] liegt, wird der
             * Datenpunkt zurückgegeben. Prognosen > 240h sind für das Diagramm uninteressant, da 
             * hier nur mit einer Auflösung von 6h gerechnet wird. */
            if (timeData.time.getTime() >= this.startDate && timeData.time.getTime() - timeData.lastRun.getTime() <= 240 * 3600e3) {
                result.values.push([timeData.time.getTime() - 60e3 * timeData.time.getTimezoneOffset(), timeData.val]);
                /* Nur wenn mindestens 3 Läufe einen Wert berechnet haben, geben wir min und max
                 * zurück. */
                if (timeData.count > 2) {
                    result.ranges.push([timeData.time.getTime() - 60e3 * timeData.time.getTimezoneOffset(), timeData.minVal, timeData.maxVal]);
                }
            }
        }
        return result;
    },


    /**
     * Liefert eine Zeitreihe mit den Winddaten. Dabei wird Windgeschrindigkeit und Windrichtung aus
     * den U und V Komponenten des Windes berechnet (Umwandlung kartesisch -> polar).
     * Außerdem wird ein color Property geschrieben, welches die Windgeschwindigkeit mit den in
     * windColors definierten Farben kategorisiert.
     * Es werden hierfür die Parameter UGRD_10 und VGRD_10 von Wxcharts gelesen.
     * @returns JSON Objekt mit dem Aufbau [{x: Timestamp, y: Windrichtung, speed: Windgeschw., color: HTML Farbstring}]
     */
    getWindData: function () {
        var uData = this.parsedData.UGRD_10;
        var vData = this.parsedData.VGRD_10;
        if (uData === undefined) { return []; }
        if (vData === undefined) { return []; }
        var timeUData = null, timeVData = null;
        var windSpeed = 0, windDir = 0;
        var result = [];
        var sector = "";

        for (var time in uData) {
            timeUData = uData[time];
            timeVData = vData[time];
            /* Nur wenn der Zeitpunkt im Intervall [jetzt-6h, letzterLauf + 240h] liegt, wird der
             * Datenpunkt zurückgegeben. Prognosen > 240h sind für das Diagramm uninteressant, da 
             * hier nur mit einer Auflösung von 6h gerechnet wird. */
            if (timeUData.time.getTime() >= this.startDate && timeUData.time.getTime() - timeUData.lastRun.getTime() <= 240 * 3600e3) {
                windSpeed = 3.6 * Math.sqrt(timeUData.val * timeUData.val + timeVData.val * timeVData.val);
                /* Formel siehe https://www.eol.ucar.edu/content/wind-direction-quick-reference */
                windDir = 270 - Math.atan2(timeVData.val, timeUData.val) * 180 / Math.PI;
                if (windDir < 0) { windDir += 360; }
                if (windDir >= 360) { windDir -= 360; }
                result.push({
                    x: timeUData.time.getTime() - 60e3 * timeUData.time.getTimezoneOffset(),
                    y: windDir,
                    speed: Math.round(windSpeed),
                    sector: this.windSectors[Math.floor((windDir + 45 / 2) / 45)],
                    color: this.getWindColor(windSpeed)
                });
            }
        }
        return result;
    },
    /**
     * Liefert den Farbcode eines Wertes aufgrund der in windColors definierten Heatmap.
     * 
     * @param {number} val Wert
     * @returns HTML Farbcode als String.
     */
    getWindColor: function (val) {
        var colors = this.windColors;
        for (var i = 1; i < colors.length; i++) {
            if (colors[i][0] > val) {
                return colors[i - 1][1];
            }
        }
        return colors[colors.length - 1][1];
    }
};