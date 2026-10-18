import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Timer;
import Toybox.WatchUi;

const COLOR_US = 0x2ECC71;
const COLOR_THEM = 0xFF5555;
const COLOR_DIM = 0xAAAAAA;

// Main in-game screen: timer, big score, my goals/assists, heart rate.
class GameView extends WatchUi.View {
    hidden var _timer = null;

    function initialize() {
        View.initialize();
    }

    function onShow() {
        _timer = new Timer.Timer();
        _timer.start(method(:onTick), 1000, true);
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
        var game = getGame();
        var w = dc.getWidth();
        var h = dc.getHeight();
        var cx = w / 2;
        var c = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;

        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();

        // Game clock (orange + PAUSED when the timer is stopped)
        var paused = !game.isRecording();
        dc.setColor(paused ? Graphics.COLOR_ORANGE : Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        var clock = formatDuration(game.elapsedMs());
        dc.drawText(cx, h * 0.15, Graphics.FONT_SMALL, paused ? "PAUSED " + clock : clock, c);

        // Team labels
        dc.setColor(COLOR_US, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.28, h * 0.30, Graphics.FONT_XTINY, "US", c);
        dc.setColor(COLOR_THEM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.72, h * 0.30, Graphics.FONT_XTINY, "THEM", c);

        // Score
        dc.setColor(COLOR_US, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.28, h * 0.50, Graphics.FONT_NUMBER_HOT, game.us().toString(), c);
        dc.setColor(COLOR_THEM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.72, h * 0.50, Graphics.FONT_NUMBER_HOT, game.them().toString(), c);
        dc.setColor(COLOR_DIM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.50, Graphics.FONT_MEDIUM, "-", c);

        // My stats
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.72, Graphics.FONT_SMALL,
            "Me  G " + game.goals() + "  A " + game.assists(), c);

        // Heart rate
        var hr = game.heartRate();
        dc.setColor(COLOR_DIM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(cx, h * 0.86, Graphics.FONT_XTINY, "HR " + (hr != null ? hr.toString() : "--"), c);
    }
}
