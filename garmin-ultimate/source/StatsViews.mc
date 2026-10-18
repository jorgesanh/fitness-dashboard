import Toybox.Application;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

// Shown after "End & save".
class SummaryView extends WatchUi.View {
    hidden var _us;
    hidden var _them;
    hidden var _g;
    hidden var _a;

    function initialize(us, them, g, a) {
        View.initialize();
        _us = us;
        _them = them;
        _g = g;
        _a = a;
    }

    function onUpdate(dc) {
        var w = dc.getWidth();
        var h = dc.getHeight();
        var cx = w / 2;
        var c = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;

        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();

        var result = _us > _them ? "WIN" : (_us < _them ? "LOSS" : "DRAW");
        var color = _us > _them ? COLOR_US : (_us < _them ? COLOR_THEM : Graphics.COLOR_WHITE);
        dc.setColor(color, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.22, Graphics.FONT_MEDIUM, result, c);

        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.45, Graphics.FONT_NUMBER_MEDIUM, _us.toString() + "-" + _them.toString(), c);
        dc.drawText(cx, h * 0.66, Graphics.FONT_SMALL, "Goals " + _g + "  Assists " + _a, c);

        dc.setColor(COLOR_DIM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.82, Graphics.FONT_XTINY, "Saved to Garmin Connect", c);
    }
}

// Totals across every saved game.
class StatsView extends WatchUi.View {
    function initialize() {
        View.initialize();
    }

    function onUpdate(dc) {
        var w = dc.getWidth();
        var h = dc.getHeight();
        var cx = w / 2;
        var c = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;

        var history = Application.Storage.getValue("history");
        if (!(history instanceof Array)) { history = []; }

        var wins = 0;
        var losses = 0;
        var goals = 0;
        var assists = 0;
        for (var i = 0; i < history.size(); i++) {
            var g = history[i];
            if (g["us"] > g["them"]) { wins++; }
            else if (g["us"] < g["them"]) { losses++; }
            goals += g["g"];
            assists += g["a"];
        }
        var n = history.size();

        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        dc.setColor(COLOR_DIM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.18, Graphics.FONT_XTINY, "SEASON (" + n + " games)", c);

        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.34, Graphics.FONT_SMALL, "W " + wins + "  L " + losses, c);
        dc.setColor(COLOR_US, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.52, Graphics.FONT_MEDIUM, goals.toString() + " G  " + assists.toString() + " A", c);

        if (n > 0) {
            dc.setColor(COLOR_DIM, Graphics.COLOR_TRANSPARENT);
            var perGame = (goals + assists).toFloat() / n;
            dc.drawText(cx, h * 0.68, Graphics.FONT_XTINY, perGame.format("%.1f") + " G+A per game", c);
        }
    }
}
