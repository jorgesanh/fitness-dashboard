import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.System;
import Toybox.Timer;
import Toybox.WatchUi;

const FLIGHT_MS = 1800;  // one pass across the screen
const PAUSE_MS = 600;    // gap before the next throw

// Shown after "End match": a frisbee flying over the final score.
class EndView extends WatchUi.View {
    hidden var _us;
    hidden var _them;
    hidden var _goals;
    hidden var _assists;
    hidden var _time;
    hidden var _startMs;
    hidden var _timer = null;

    function initialize(game) {
        View.initialize();
        _us = game.us;
        _them = game.them;
        _goals = game.goals;
        _assists = game.assists;
        _time = game.matchTime();
        _startMs = System.getTimer();
    }

    function onShow() {
        _timer = new Timer.Timer();
        _timer.start(method(:onTick), 50, true);
    }

    function onHide() {
        if (_timer != null) {
            _timer.stop();
            _timer = null;
        }
    }

    function onTick() as Void {
        WatchUi.requestUpdate();
    }

    function onUpdate(dc) {
        var w = dc.getWidth();
        var h = dc.getHeight();
        var c = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;

        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();

        var elapsed = (System.getTimer() - _startMs) % (FLIGHT_MS + PAUSE_MS);
        if (elapsed < FLIGHT_MS) {
            drawFrisbee(dc, w, h, elapsed.toFloat() / FLIGHT_MS);
        }

        dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.47, Graphics.FONT_XTINY, _time, c);

        dc.setColor(Graphics.COLOR_GREEN, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.3, h * 0.64, Graphics.FONT_NUMBER_MEDIUM, _us.toString(), c);
        dc.setColor(Graphics.COLOR_RED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.7, h * 0.64, Graphics.FONT_NUMBER_MEDIUM, _them.toString(), c);

        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.83, Graphics.FONT_SMALL,
            "G " + _goals + "   A " + _assists, c);
    }

    // t = 0..1 across one flight: left to right in a gentle arc.
    hidden function drawFrisbee(dc, w, h, t) {
        var rx = w * 0.09;
        var x = -rx + (w + 2 * rx) * t;
        var y = h * 0.34 - Math.sin(Math.PI * t) * h * 0.14;
        // Disc tilts flatter toward the end of the throw.
        var ry = rx * (0.45 - 0.15 * t);

        // Fading trail behind the disc
        dc.setColor(Graphics.COLOR_DK_GRAY, Graphics.COLOR_TRANSPARENT);
        for (var i = 1; i <= 4; i++) {
            var tt = t - i * 0.04;
            if (tt < 0) { break; }
            var tx = -rx + (w + 2 * rx) * tt;
            var ty = h * 0.34 - Math.sin(Math.PI * tt) * h * 0.14;
            dc.fillCircle(tx, ty, 4 - i * 0.8);
        }

        // Disc body, rim and inner ring
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.fillEllipse(x, y, rx, ry);
        dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
        dc.drawEllipse(x, y, rx * 0.65, ry * 0.65);
        dc.setPenWidth(2);
        dc.drawEllipse(x, y, rx, ry);
        dc.setPenWidth(1);
    }
}

// Any button closes the app.
class EndDelegate extends WatchUi.InputDelegate {
    function initialize() {
        InputDelegate.initialize();
    }

    function onKey(evt) {
        System.exit();
        return true;
    }
}
