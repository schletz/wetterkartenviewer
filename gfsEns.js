/* jshint strict:global */
/* globals $, localStorage, console, cfsrMeans, cfsrMeansYear */
"use strict";

/* 
 * DATE Erweiterungen 
 */
Date.prototype.getIsoDate = function () {
    var month = this.getUTCMonth() + 1;
    var day = this.getUTCDate();
    var hour = this.getUTCHours();
    var minute = this.getUTCMinutes();
    var second = this.getUTCSeconds();
    return this.getUTCFullYear() + "-" +
        (month < 10 ? "0" : "") + month + "-" +
        (day < 10 ? "0" : "") + day + "T" +
        (hour < 10 ? "0" : "") + hour + ":" +
        (minute < 10 ? "0" : "") + minute + ":" +
        (second < 10 ? "0" : "") + second + "Z";
};

var Converter = {
    kToC: function (val) { return val - 273.15; }
};
/*
 * GfsEns Object
 */

var GfsEns = {
    version: "20170526_1",
    parsedData: [],
    /* Der Startzeitpunkt der Diagrammausgabe ist die letzte volle 6. Stunde, die aber mindestens 
     * 6 Stunden her ist. Wird in den getData Methoden verwendet. */
    startDate: new Date(Math.floor((Date.now() - 6 * 3600e3) / 6 / 3600e3) * 6 * 3600e3).getTime(),
    planetOsUrl: "https://api.planetos.com/v1/datasets/noaa_gfs_pgrb2_global_forecast_recompute_0.25degree/point?var={param}" +
    "&z={z}&lat={lat}&lon={lon}&count={count}&reftime_start={firstRun}&reftime_end={lastRun}&apikey=a7017583aeb944d2b8bfec81ff9a2363",
    lat: 0,
    lon: 0,
    get gfsLat() { return Math.round(this.lat / 0.25) * 0.25; },
    get gfsLon() { return Math.round(this.lon / 0.25) * 0.25; },
    get cfsrLat() { return Math.round(this.lat); },
    get cfsrLon() { return Math.round(this.lon); },
    newestLastRun: 0,                    // Der neueste Run-Timestamp aller Datensätze
    oldestLastRun: Number.MAX_VALUE,     // Der älteste Run-Timestamp aller Datensätze
    /* Alle abzufragenden Daten. Jeder Eintrag ist ein Ajax Request, bei dem die Daten von
     * PlanetOs angefordert werden. Alle Werte werden mit der Transform-Funktion, wenn angegeben,
     * umgewandelt. */
    requests: [
        /* Temperatur auf 850hpa */
        { param: "tmpprs", zIndex: 25, loadHistory: true },
        /* Temperatur auf 500hpa */
        { param: "tmpprs", zIndex: 18 },
        /* Temperatur in Höhen über dem Boden. Wir brauchen nur 2m (z: fist) */
        { param: "tmp_m", zIndex: "first", loadHistory: true },

        /* Geopot Höhe 500hpa, die Transformation erzeugt die Abweichung vom Mittel in dam. */
        { param: "hgtprs", zIndex: 18 },
        /* Geopot Höhe 1000hpa, die Transformation erzeugt die Abweichung vom Mittel in dam. */
        { param: "hgtprs", zIndex: 30 },

        /* Druck reduziert auf Meeresniveau. */
        //{ param: "prmslmsl", zIndex: "first", transform: function (val) { return val / 100.0; } },

        /* Vertical velocity (pressure) @700hpa" */
        //{ param: "vvelprs", zIndex: 12 },

        /* Relative Feuchte */
        { param: "rhprs", zIndex: "all" },

        /* 3h Niederschlag */
        { param: "apcpsfc_3_Hour_Accumulation" },
        /* U und V Komponente des 1000 hPa Windws (z: first wird als Standard gesetzt) */
        { param: "vgrdprs", zIndex: "last" },
        { param: "ugrdprs", zIndex: "last" }
        /*
        { param: "vgrd_m" },
        { param: "ugrd_m" }
        */
    ],
    requestsLoaded: 0,    // Für die Bestimmung, wann alle Ajax Requests fertig sind.
    windColors: [[0, '#CCCCCC'], [10, '#6E79FA'], [20, '#1AFF00'], [30, '#FFE900'], [40, '#FF0000'], [50, '#CC0074']],
    windSectors: ["N", "NO", "O", "SO", "S", "SW", "W", "NW", "N"],

    onReady: function (source) { return; },
    onError: function (source, message, details) { return; },
    onLoaded: function (source, message, details) { return; },

    /**
     * Liefert die URL, mit der die in RequestData geforderten Daten von PlanetOs geladen werden.
     * 
     * @param {object} requestData Parameter des Requests in der Form
     * { param: string, z: string, transform: function (val), firstRun: object, lastRun: object, loadHistory: boolean }
     * @returns URL für den AJAX Request.
     */
    getRequestUrl: function (requestData) {
        var count = 1000000;
        if (requestData.param === undefined) { return ""; }
        if (requestData.zIndex === undefined) { requestData.zIndex = "first"; }
        if (requestData.firstRun === undefined) { requestData.firstRun = new Date(); }
        if (requestData.lastRun === undefined) { requestData.lastRun = new Date(); }

        var url = this.planetOsUrl;

        if (requestData.param == "reftime") {
            count = 1; requestData.zIndex = "first";
            url = url.replace("reftime_start={firstRun}&reftime_end={lastRun}", "context=reftime_time1_isobaric3_lat_lon");
        }
        /* Die Auflösung der GFS Daten beträgt 0.25°, daher runden wir auf das nächste volle
         * Viertel. */
        return url.replace("{lat}", this.gfsLat).
            replace("{lon}", this.gfsLon).
            replace("{param}", requestData.param).
            replace("{z}", requestData.zIndex).
            replace("{count}", count).
            replace("{firstRun}", requestData.firstRun.getIsoDate()).
            replace("{lastRun}", requestData.lastRun.getIsoDate());

    },

    init: function (param) {
        var self = this;

        self.lat = param.lat || 48;
        self.lon = param.lon || 16.3;
        self.loadData();
    },

    /**
     * Führt die AJAX Requests durch und startet für jeden gelesenen Datensatz die Methode
     * parseData. Zuerst wird ein reftime Request abgesetzt, der das Datum des letzten Laufes
     * ermittelt. Ist dieser Lauf schon im localStorage, wird von diesem gelesen. Nur wenn
     * ein neuerer Lauf vorhanden ist, wird aus dem Web gelesen.
     * 
     * @param {number} lastRun Der Timestamp (ms seit 1.1.1970) des aktuellsten Laufes. Wenn nicht 
     * angegeben, wird mit einem reftime request von PlanetOs das Datum des letzten Laufes gelesen. 
     * Wenn angegeben, werden alle Requests in requests geladen, in die Variable parsedData geschrieben
     * und nach dem letzten Request
     * die Funktion onReady aufgerufen. Außerdem werden die Daten in den localStorage mit dem Key
     * parsedData und lastRun geschrieben.
     * @returns 
     */
    loadData: function (lastRun) {
        var self = this;
        var url = "";
        /* Kein letzter Lauf? Diesen anfordern */
        if (lastRun === undefined) {
            url = self.getRequestUrl({ param: "reftime" });

            $.ajax({ url: url, dataType: "json" }).done(function (data) {
							console.log(data);
                var lastRun = new Date(data.entries[0].classifiers.reference_time).getTime();
                /* Nur volle 6h als letzten Lauf nehmen. Manchmal kommen zwischenzeiten, wenn
                 * es beim Import Probleme gab. Um double Fehler zu vermeiden, wird 1 min
                 * dazuaddiert. */
                lastRun = new Date(Math.floor((lastRun + 60e3) / 6 / 3600e3) * 6 * 3600e3);
                if (isNaN(lastRun.getTime())) { return self.onError(self, "READ_LAST_RUN_FAILED"); }

                self.onLoaded(self, "Letzter Lauf auf PlanetOs: " + lastRun.toISOString());
                self.loadData(lastRun.getTime());
            }).fail(function () {
                self.onError(self, "REQUEST_FAILED", url);
            });
            return;
        }

        /* Wurde dieser Lauf schon einmal im localStorage gespeichert? Dann lesen wir nicht neu,
         * sondern setzen parsedData auf die gespeicherten Daten. */
        if (localStorage.getItem("version") == self.version &&
            localStorage.getItem("lastRun") == lastRun &&
            localStorage.getItem("gfsLat") == self.gfsLat &&
            localStorage.getItem("gfsLon") == self.gfsLon &&
            localStorage.getItem("parsedData") !== null) {
            self.onLoaded(self, "Daten im Local Storage aktuell.");
            self.parsedData = JSON.parse(localStorage.getItem("parsedData"));
            self.onReady(self);
            return true;
        }
        else {
            self.requests.forEach(function (item) {
                item.lastRun = new Date(lastRun);
                item.firstRun = new Date(lastRun);
                /* loadHistory lädt die letzten 4 Läufe. Dazu wird 1 Tag abgezogen (4 Läufe pro Tag)
                 * und 1 min dazuaddiert, da die API mit >= vergleicht. Sonst wären es 5 Läufe. */
                if (item.loadHistory) {
                    item.firstRun.setUTCDate(item.firstRun.getUTCDate() - 1);
                    item.firstRun.setUTCMinutes(1);
                }
                url = self.getRequestUrl(item);

                $.ajax({ url: url, dataType: "json" }).done(function (data) {
                    self.parseData(data, item.param);
                    self.requestsLoaded++;
                    self.onLoaded(self, "Parameter geladen (" +
                        self.requestsLoaded + "/" + self.requests.length + ")",
                        item.param);
                    /* Alles geladen? Dann in den localStorage schreiben und onReady aufrufen. */
                    if (self.requestsLoaded == self.requests.length) {
                        self.postprocessData();
                        self.onReady(self);
                        /* Die Daten nur schreiben, wenn alle Datensätze vom gleichen Lauf kommen.
                         * Bei fehlerhaften Importen ist das nicht immer der Fall. */
                        if (self.newestLastRun == self.oldestLastRun) {
                            localStorage.setItem("parsedData", JSON.stringify(self.parsedData));
                            localStorage.setItem("lastRun", lastRun);
                            localStorage.setItem("gfsLat", self.gfsLat);
                            localStorage.setItem("gfsLon", self.gfsLon);
                            localStorage.setItem("version", self.version);
                        }
                        return true;
                    }
                }).fail(function () {
                    self.onError(self, "REQUEST_FAILED", url);
                });
            });
        }

        return true;
    },

    /**
     * Speichert die geladenen Daten in parsedData. Es wird ein JSON Array in der Form
     * [{param: string, z: number, time: number, val: number, count: number, minVal: number, maxVal: number, lastRun: number}]
     * erstellt.
     * 
     * @param {object} data Die JSON Daten von PlanetOs.
     * @param {string} param Der gelesene Parameter (z. B. tmp_m).
     * @param {function} transform Die Transformationsfunktion, die für jeden Wert ausgeführt wird.
     */
    parseData: function (data, param) {
        var self = this;
        var indexes = [];
        /* Die CFSR Daten 1981 - 2010 haben eine Auflösung von 1°. */
        var meanLat = self.cfsrLat;
        var meanLon = self.cfsrLon;

        data.entries.forEach(function (item) {
            /* Z für UTC bei Befarf einfügen. */
            var run = /Z$/.test(item.axes.reftime) ? new Date(item.axes.reftime).getTime() :
                new Date(item.axes.reftime + "Z").getTime();

            /* Z für UTC bei Befarf einfügen. */
            var time = /Z$/.test(item.axes.time) ? new Date(item.axes.time).getTime() :
                new Date(item.axes.time + "Z").getTime();

            var z = 0;
            /* Manche Daten haben kein z. Sie werden mit z = 0 gespeichert. */
            if (item.axes.z !== undefined) { z = 1 * item.axes.z; }

            var mean = null;
            var val = 1 * item.data[param];
            if (indexes[z] === undefined) { indexes[z] = []; }
            if (indexes[z][time] === undefined) {
                /* Im Array cfsrMeans nachsehen, ob ein Mittelwert zu diesem Parameter
                 * und diesem Z Wert existiert. Die Mittelwerte haben eigentlich kein Jahr,
                 * aber in cfsrMeansYear ist das Jahr angegeben, auf welches sich die dortigen
                 * Timestamps beziehen. */
                try {
                    var timeForMean = new Date(Math.round(time / (6 * 3600e3)) * 6 * 3600e3);
                    timeForMean.setUTCFullYear(cfsrMeansYear);
                    timeForMean = timeForMean.getTime();
                    mean = cfsrMeans[meanLon][meanLat][param][z][timeForMean];
                }
                catch (e) { }
                self.parsedData.push({
                    param: param,
                    z: z,
                    time: time,
                    val: val,
                    count: 1,
                    minVal: val,
                    maxVal: val,
                    mean: mean,
                    lastRun: run
                });
                indexes[z][time] = self.parsedData.length - 1;
            }
            /* Wurde der Messwert für diesen Zeitpunkt schon gelesen, dann ist es eine Prognose
             * eines anderen Laufes. Hier werden die Daten aktualisiert. */
            else {
                var currentItem = self.parsedData[indexes[z][time]];
                if (currentItem.lastRun < run) {
                    currentItem.val = val;
                    currentItem.lastRun = run;
                }
                currentItem.count++;
                currentItem.minVal = Math.min(currentItem.minVal, val);
                currentItem.maxVal = Math.max(currentItem.maxVal, val);
            }
        });
        return true;
    },

    /**
     * Erstellt Parameter, die sich durch Berechnung aus anderen Parametern ergeben. Aktuell
     * wird die relative Topografie berechnet, also die Differenz zwischen der Höhe der 
     * 500 und 1000 hPa Druckschicht, und die maximale relative Feuchte im Bereich von 1000 - 700hPa
     * berechnet.
     * 
     * @returns 
     */
    postprocessData: function () {
        var self = this;
        /* Diese Parameter dienen zur Berechnung der Daten. */
        var gpt500Item = null;
        var gpt1000Item = null;
        var maxRhprs = { time: 0, val: 0, lastRun: 0 };

        var time = 0;
        var len = self.parsedData.length;       // Da das Array wächst, wird die Länge vorberechnet.
        var item = null;
        var now = new Date().getTime();

        /* Highcharts und die nachfolgende Bearbeitung benötigen nach der Zeit sortierte Daten. */
        self.parsedData.sort(function (a, b) { return a.time - b.time; });

        for (var i = 0; i < len; i++) {
            item = self.parsedData[i];
            time = item.time;
            /* Ermitteln, wie alt die Prognose der angezeigten Datenpunkte ist. Nur wenn alle
             * angezeigten Werte das gleiche Laufdatum haben, werden die Daten in den Local Storage
             * gespeichert. */
            if (time >= now) {
                self.newestLastRun = Math.max(self.newestLastRun, item.lastRun);
                self.oldestLastRun = Math.min(self.oldestLastRun, item.lastRun);
            }

            if (item.param == "hgtprs" && item.z == 100000) {
                gpt1000Item = item;
            }
            if (item.param == "hgtprs" && item.z == 50000) {
                gpt500Item = item;
            }
            if (item.param == "rhprs" && item.z >= 50000) {
                maxRhprs.time = time; maxRhprs.val = Math.max(maxRhprs.val, item.val); maxRhprs.lastRun = item.lastRun;
            }
            /* Nächster Zeitwert ist anders? Die Parameter - wenn sie gefunden wurden - schreiben
             * (klassischer Gruppenwechsel) */
            if (i + 1 == len || self.parsedData[i + 1].time != time) {
                if (gpt500Item !== null && gpt1000Item !== null) {
                    self.parsedData.push({
                        param: "retop",
                        z: 50000,
                        time: gpt500Item.time,
                        val: gpt500Item.val - gpt1000Item.val,
                        count: 1,
                        mean: gpt500Item.mean - gpt1000Item.mean,
                        minVal: gpt500Item.val - gpt1000Item.val,
                        maxVal: gpt500Item.val - gpt1000Item.val,
                        lastRun: gpt500Item.lastRun
                    });
                }
                if (maxRhprs.time !== 0) {
                    self.parsedData.push({
                        param: "maxRhprs",
                        z: 70000,
                        time: maxRhprs.time,
                        val: maxRhprs.val,
                        count: 1,
                        mean: null,
                        minVal: maxRhprs.val,
                        maxVal: maxRhprs.val,
                        lastRun: maxRhprs.lastRun
                    });
                }
                gpt1000Item = null;
                gpt500Item = null;
                maxRhprs.time = 0; maxRhprs.val = 0;
            }
        }
        self.onLoaded(self, "Daten fertig geladen",
            "Lauf: " + new Date(self.oldestLastRun).toISOString() + " - " +
            new Date(self.newestLastRun).toISOString());
        return true;
    },


    /**
     * Liefert ein JSON Objekt, welches eine Zeitreihe für den Parameter zurückgibt (values) oder
     * die Min und Max Werte der Läufe (Property ranges).
     * @example var dataSource = getData("tmpprs", 85000).ranges;
     * 
     * @param {string} param Der Parametername. tmpprs wenn nicht übergeben wird.
     * @returns Ein JSON Objekt mit dem Aufbau
     * {values: [[Timestamp, Value], ...], ranges: [[Timestamp, Min, Max], ...]}
     */
    getData: function (param, z, transform) {
        if (param === undefined) { param = "tmpprs"; }
        if (z === undefined) { z = 0; }
        if (transform === undefined) { transform = function (val) { return val; }; }

        var self = this;
        var result = { values: [], ranges: [], means: [] };
        this.parsedData.forEach(function (item) {
            var time = item.time;
            if (item.param == param && item.z == z) {
                if (time >= self.startDate) {
                    result.values.push([time - 60e3 * new Date(time).getTimezoneOffset(), transform(item.val)]);
                    if (item.mean !== null) {
                        result.means.push([time - 60e3 * new Date(time).getTimezoneOffset(), transform(item.mean)]);
                    }
                    /* Nur wenn mindestens 3 Läufe einen Wert berechnet haben, geben wir min und max
                     * zurück. */
                    if (item.count > 2) {
                        result.ranges.push([time - 60e3 * new Date(time).getTimezoneOffset(), transform(item.minVal), transform(item.maxVal)]);
                    }
                }
            }
        });
        return result;
    },

    /**
     * Berechnet den Mittelwert aller Messdaten eines bestimmten Parameters und einer bestimmten
     * Ebene.
     * 
     * @param {string} param Der zu mittelnde Parameter.
     * @param {number} z Die vertikale Schicht (z. B. 85000 für 850hPa)
     * @param {function} transform Die Transformationsfunktion, die für jedes Element vor der 
     * Mittelwertbildung angewandt wird.
     * @param {number} defaultVal Der Standardwert, der gelifert wird, wenn keine Daten gefunden
     * wurden.
     * @returns 
     */
    getMean: function (param, z, transform, defaultVal) {
        if (defaultVal === undefined) { defaultVal = null; }
        if (transform === undefined) { transform = function (val) { return val; }; }
        var sum = 0;
        var count = 0;

        this.parsedData.forEach(function (item) {
            if (item.param == param && item.z == z) {
                sum += transform(item.val);
                count++;
            }
        });
        if (count > 0) { return sum / count; }
        return defaultVal;
    },
    /**
     * Liefert eine Zeitreihe mit den Winddaten. Dabei wird Windgeschrindigkeit und Windrichtung aus
     * den U und V Komponenten des Windes berechnet (Umwandlung kartesisch -> polar).
     * Außerdem wird ein color Property geschrieben, welches die Windgeschwindigkeit mit den in
     * windColors definierten Farben kategorisiert.
     * Es werden hierfür die Parameter vgrd_m und ugrd_m aus parsedData gelesen.
     * @returns JSON Objekt mit dem Aufbau [{x: Timestamp, y: Windrichtung, speed: Windgeschw., color: HTML Farbstring}]
     */
    getWindData: function (z) {
        var self = this;
        var vgrd = { time: 0, val: 0 };
        var ugrd = { time: 0, val: 0 };
        var windSpeed = 0, windDir = 0, result = [];

        if (z === undefined) { z = 100000; }
        this.parsedData.forEach(function (item) {
            var time = item.time;
            /* Nur wenn der Zeitpunkt im Intervall [jetzt-6h, letzterLauf + 240h] liegt, wird der
             * Datenpunkt zurückgegeben. Prognosen > 240h sind für das Diagramm uninteressant, da 
             * hier nur mit einer Auflösung von 6h gerechnet wird. */
            if (time >= self.startDate) {
                if (item.param == "vgrdprs" && item.z == z) {
                    vgrd.time = time; vgrd.val = item.val;
                }
                if (item.param == "ugrdprs" && item.z == z) {
                    ugrd.time = time; ugrd.val = item.val;
                }
                if (vgrd.time == time && ugrd.time == time) {
                    windSpeed = 3.6 * Math.sqrt(vgrd.val * vgrd.val + ugrd.val * ugrd.val);
                    /* Formel siehe https://www.eol.ucar.edu/content/wind-direction-quick-reference */
                    windDir = 270 - Math.atan2(vgrd.val, ugrd.val) * 180 / Math.PI;
                    if (windDir < 0) { windDir += 360; }
                    if (windDir >= 360) { windDir -= 360; }
                    result.push({
                        x: time - 60e3 * new Date(time).getTimezoneOffset(),
                        y: windDir,
                        speed: Math.round(windSpeed),
                        sector: self.windSectors[Math.floor((windDir + 45 / 2) / 45)],
                        color: self.getWindColor(windSpeed)
                    });

                    vgrd.time = 0;
                    ugrd.time = 0;
                }
            }
        });
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