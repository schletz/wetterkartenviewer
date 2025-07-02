/* jshint strict:global */
/* globals $, console, Weathermap, window */

"use strict";
var ModelChooserViewModel = {
    lastRun: {},
    _previewImages: [],
    container: null,

    get logContainer() { return $(this.container).parent().find("#log"); },
    get previewImages() { return this._previewImages; },
    set previewImages(value) {
        var self = this;
        var rand = Date.now();
        var model = value.model;
        var modelContainer = $('[data-model="' + model + '"]');
        value.images.forEach(function (item) {
            var imgContainer = $("<div>").addClass("runImage");
            imgContainer.append($("<img>").attr("src", item.url + "?rnd=" + rand));
            imgContainer.data("runHour", item.runHour);
            imgContainer.data("model", model);
            imgContainer.on("click", function () {
                self.onModelPreviewClick(this);
            });
            $(modelContainer).append(imgContainer);
        });
        this.container.append(modelContainer);
    },

    onModelPreviewClick: function (source) {
        // Startet das Programm, wenn alle Läufe angeklickt wurden. Im Moment ist nur der 
        // GFS Lauf zu wählen. Es kann aber auch ein anderer Lauf zusätzlich angegeben werden.
        // Hier ist dann im if für jedes Modell der Zustand von lastRun zu prüfen.
        $(source).parent().find(".runImage").css("border", "0px");
        $(source).css("border", "3px solid blue");

        var runHour = 1 * $(source).data("runHour");
        var model = $(source).data("model");
        this.lastRun[model] = Date.fromUTCHours(runHour);
        if (this.lastRun.gfs) {
            Weathermap.lastRun.gfs = this.lastRun.gfs;
            Weathermap.lastRun.iconWetter3 = this.lastRun.gfs;
            this.destroyUi();
            Weathermap.initUi("panelsPage");
        }
    },
    /*
    loadWetter3IconRun: function (initString) {
        // Das Script http://www.wetter3.de/initicon setzt die Variable init1.
        if (typeof initString !== "undefined" && (Weathermap.lastRun.iconWetter3 = Date.fromW3InitString(initString))) {
            this.logContainer.append('<p>Gelesener ICON Lauf von Wetter3 über JS:' + Weathermap.lastRun.iconWetter3.toISOString() + "<p>");
            return;
        }
    },    
    */

    appendRnd: function (src) {
        if (!src) { src = ""; }
        var newSrc = "", filename = "", ext = "";
        /* Keine GET Parameter? Dann ist das eine normales Bild URL mit filename.ext */
        if (src.indexOf("?") === -1) {
            filename = src.substring(0, src.lastIndexOf("."));
            ext = src.substring(src.lastIndexOf("."));
            newSrc = filename + Date.now() + ext;
        }
        /* Bei GET Parametern den Parameter rand mit der Zeit in ms anhängen- */
        else {
            newSrc = src + "&rand=" + Date.now();
        }
        return newSrc;
    },

    loadDiagrams: function () {
        var self = this;
        const maxWidth = window.innerWidth / 2 - 30;
        /* Hängt für jedes img Element, welches data-src besitzt, eine Zufallszahl an.
         * So wird der Cache umgangen. */
        $("img[data-src0]").each(function (item) {
            var src = $(this).data("src0");
            // Damit 2 Bilder nebeneinander Platz haben, wird die Größe berechnet. Per CSS
            // und 50% Breite kann die Maximale Größe bei vorgegebener Proportion nicht gesetzt werden.
            if ($(this).attr("width") > maxWidth) {
                $(this).attr("height", $(this).attr("height") * maxWidth / $(this).attr("width"));
                $(this).attr("width", maxWidth);
            }

            $(this).attr("src", self.appendRnd(src));
            $(this).data("clickIndex", 0);

            // Beim Klicken auf das Bild von src0 auf src1 auf src2, ... tauschen.
            $(this).on("click", function () {
                var idx = $(this).data("clickIndex") + 1;
                var newSrc = $(this).data("src" + idx);
                if (!newSrc) {
                    idx = 0;
                    newSrc = $(this).data("src0");
                }
                $(this).attr("src", self.appendRnd(newSrc));
                $(this).data("clickIndex", idx);
            });
        });
    }
};

ModelChooserViewModel.initUi = function (container) {
    this.container = $("#" + container);
    this.loadDiagrams();
    this.container.show();
    $("#diagramPage").show();
    this.previewImages = {
        model: "gfs", images: [
            { runHour: 0, url: "http://www.wetter3.de/Animation_00_UTC/240_1.gif" },
            { runHour: 6, url: "http://www.wetter3.de/Animation_06_UTC/240_1.gif" },
            { runHour: 12, url: "http://www.wetter3.de/Animation_12_UTC/240_1.gif" },
            { runHour: 18, url: "http://www.wetter3.de/Animation_18_UTC/240_1.gif" },
        ]
    };
    /*
    this.previewImages = {
        model: "arpege", images: [
            { runHour: 0, url: "http://wxcharts.eu/charts/arpege/germany/00/overview_102.jpg" },
            { runHour: 6, url: "http://wxcharts.eu/charts/arpege/germany/06/overview_072.jpg" },
            { runHour: 12, url: "http://wxcharts.eu/charts/arpege/germany/12/overview_102.jpg" },
            { runHour: 18, url: "http://wxcharts.eu/charts/arpege/germany/18/overview_060.jpg" },
        ]
    };
    */
    // this.loadWetter3IconRun(init1);
};

ModelChooserViewModel.destroyUi = function () {
    $("#diagramPage").hide();
    this.container.hide();
};