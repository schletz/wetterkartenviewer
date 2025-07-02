/* jshint strict:global */
/* globals $, Image, window, console */

"use strict";
/**
 * Erzeugt ein Datumsobjekt, welches auf den aktuellen Lauf verweist. Dabei wird das Intervall der
 * Läufe und die Verzögerung der Datenaufbereitung berücksichtigt. 
 * @example Date.fromRunParam(6,5) // Liefert am 12.2.2017 um 15:00 UTC den Wert 12.2.2017 6:00 UTC
 * 
 * @param {number} runsInterval Der Abstand zwischen den Läufen (z. B: 6 für 4x täglich)
 * @param {number} delay Die Verzögerung, bis die Daten zur Verfügungs stehen.
 * @returns Das Datumsobjekt, wann der aktuelle Lauf gestartet wurde.
 */
Date.fromRunParam = function (runsInterval, delay) {
    if (isNaN(runsInterval)) { runsInterval = 6; }
    if (isNaN(delay)) { delay = 0; }

    runsInterval *= 3600000;
    var d = new Date();
    d.setTime(d.getTime() - delay * 3600e3);
    d.setTime(Math.floor(d.getTime() / runsInterval) * runsInterval);
    return d;
};
/**
 * Erzeugt ein Datumsobjekt, welches aus dem wetter3 Datumsstring gelesen wird.
 * Dieser String ist unter http://www1.wetter3.de/initarpege abrufbar und legt eine Variable
 * var init1 = 'Mi, 01-03-2017 06 UTC' an.
 * 
 * @param {string} val Der Datumsstring.
 * @returns Das Datumsobjekt, welches dem Datum entspricht. Ist der String ungültig, wird der 
 * Zeitwert der letzten vollen 6 Stunden, die aber mindestens 6 Stunden zurück liegen, zurückgegeben.
 */
Date.fromW3InitString = function (val) {
    if (val === undefined) { val = ""; }
    var d = new Date(0);
    var matches = val.match(/(\d+)-(\d+)-(\d+)\s(\d+)\s+UTC/i);
    if (matches !== null) {
        d.setUTCFullYear(matches[3]);
        d.setUTCMonth(matches[2] - 1);  // Das Monat beginnt in JS bei 0.
        d.setUTCDate(matches[1]);
        d.setUTCHours(matches[4]);
        return d;
    }
    else {
        return null;
    }
};

/**
 * Erzeugt ein Datumsobjekt mit der übergebenen vollen Stunde (0min, 0sek). Würde das Datum in der
 * Zukunft liegen, so wird der Vortag genommen.
 * Date.fromUTCHours(4) liefet also am 3.2.2017 3h UTC das Datum 2.2.2017 4:00:00 UTC
 * @param {number} hour Die Stunde.
 * @returns Das Datumsobjekt, welches den oberen Regeln entspricht.
 */
Date.fromUTCHours = function (hour) {
    var d = new Date();
    if (d.getUTCHours() < hour) {
        d.setUTCDate(d.getUTCDate() - 1);
    }
    d.setUTCHours(hour);
    d.setUTCMinutes(0);
    d.setUTCSeconds(0);
    d.setUTCMilliseconds(0);
    return d;
};

Date.prototype.weekdays = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];
Date.prototype.monthName = ["Jän", "Feb", "März", "Apr", "Mai", "Juni", "Juli", "Aug", "Sep", "Okt", "Nov", "Dez"];

/**
 * Formatiert das Datum in der Form YYYYMMDD. Dies wird bei manchen URLs als Parameter verwendet.
 * 
 * @returns Ein String der Form YYYYMMDD
 */
Date.prototype.getUTCymd = function () {
    var year = this.getUTCFullYear();
    var month = this.getUTCMonth() + 1;
    var day = this.getUTCDate();

    if (month < 10) { month = "0" + month; }
    if (day < 10) { day = "0" + day; }

    return "" + year + month + day;
};

/**
 * Formatiert das Datum in der Form YYYYMMDDHH. Dies wird bei manchen URLs als Parameter verwendet.
 * 
 * @returns Ein String der Form YYYYMMDDHH
 */
Date.prototype.getUTCymdh = function () {
    var hour = this.getUTCHours();
    hour = hour < 10 ? "0" + hour : "" + hour;

    return this.getUTCymd() + hour;
};

/**
 * Liefert den Datumsstring als deutsches Datum in der Form TTT, T. MMM JJJJ
 * (z. B. Mo, 7. Aug 2017)
 * 
 * @returns Der Datumsstring
 */
Date.prototype.getGermanStr = function (withTime) {
    withTime = withTime || false;

    var year = this.getFullYear();
    var month = this.getMonth();
    var day = this.getDate();
    var formattedStr = this.weekdays[this.getDay()] + ", " + day + ". " + this.monthName[month] + " " + year;
    if (withTime) { formattedStr += " " + ("00" + this.getUTCHours()).slice(-2) + "Z"; }
    return formattedStr;

};
/**
 * Gibt das julianische Datum des Datumsobjektes zurück. Dabei wird immer 12h UTC angenommen.
 * 
 * @returns Das iulianische Datum.
 */
Date.prototype.jd = function () {
    /* 1.1.1970 12h UTC = JD 2440588 */
    return Math.floor(0.5 + this.getTime() / 86400000.0) + 2440588;
};

/**
 * Gibt das Datum des Ostersonntags im gregorianischen Kalender zurück.
 * Quelle: Meeus. Astronomical Algorithms, 2nd Ed, p67
 * @param {number} year Das Jahr
 * 
 * @returns Ein Datumsobjekt, welches den Ostersonntag um 12:00 in Lokalzeit angibt.
 */
Date.fromEasterDate = function (year) {
    var a = year % 19;
    var b = Math.floor(year / 100);
    var c = year % 100;
    var d = Math.floor(b / 4);
    var e = b % 4;
    var f = Math.floor((b + 8) / 25);
    var g = Math.floor((b - f + 1) / 3);
    var h = (19 * a + b - d - g + 15) % 30;
    var i = Math.floor(c / 4);
    var k = c % 4;
    var l = ((32 + 2 * e + 2 * i - h - k) % 7);
    var m = Math.floor((a + 11 * h + 22 * l) / 451);
    var n = Math.floor((h + l - 7 * m + 114) / 31);
    var p = ((h + l - 7 * m + 114) % 31);
    return new Date(year, n - 1, p + 1, 12, 0, 0, 0);
};

/**
 * Gibt true zurück, wenn das angegebene Datum ein österreichischer Feiertag ist.
 * Sonntage werden - wenn sie nicht auf einen Feiertag fallen - nicht als Feiertag zurück geliefert.
 * 
 * @returns true bei einem Feiertag, falls bei keinem Feiertag.
 */
Date.prototype.isHoliday = function () {
    var year = this.getFullYear();
    var month = this.getMonth() + 1;
    var day = this.getDate();
    var jd = this.jd();
    var easter = null;

    /* Fixe Feiertage */
    if (month == 1 && day == 1) { return true; }
    if (month == 1 && day == 6) { return true; }
    if (month == 5 && day == 1) { return true; }
    if (month == 8 && day == 15) { return true; }
    if (month == 10 && day == 26) { return true; }
    if (month == 11 && day == 1) { return true; }
    if (month == 12 && day == 25) { return true; }
    if (month == 12 && day == 26) { return true; }

    /* Feiertage mit Bezug auf den Ostersonntag */
    if (month >= 3 && month <= 6) {
        easter = Date.fromEasterDate(year).jd();
        if (jd == easter) { return true; }      // Ostersonntag
        if (jd == easter + 1) { return true; }  // Ostermontag
        if (jd == easter + 39) { return true; } // Christi Himmelfahrt
        if (jd == easter + 49) { return true; } // Pfingstsonntag
        if (jd == easter + 50) { return true; } // Pfingstmontag
        if (jd == easter + 60) { return true; } // Fronleichnam
    }
    return false;
};