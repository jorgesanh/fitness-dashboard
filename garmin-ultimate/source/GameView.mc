import Toybox.Attention;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.System;
import Toybox.Timer;
import Toybox.WatchUi;

// One screen: time of day, match clock, the score, point clock, my goals/assists.
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
        var c = Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER;

        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();

        // Time of day (small) and match clock
        var now = System.getClockTime();
        dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.12, Graphics.FONT_XTINY,
            now.hour.format("%d") + ":" + now.min.format("%02d"), c);
        drawMatchClock(dc, w / 2, h * 0.25, game.matchTime());

        // Score: us green, them red
        dc.setColor(Graphics.COLOR_GREEN, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.3, h * 0.5, Graphics.FONT_NUMBER_HOT, game.us.toString(), c);
        dc.setColor(Graphics.COLOR_RED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.7, h * 0.5, Graphics.FONT_NUMBER_HOT, game.them.toString(), c);

        // Time since last point (or a prompt before the match starts)
        if (game.isStarted()) {
            dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
            dc.drawText(w / 2, h * 0.69, Graphics.FONT_XTINY, "Point " + game.pointTime(), c);
        } else {
            dc.setColor(Graphics.COLOR_GREEN, Graphics.COLOR_TRANSPARENT);
            dc.drawText(w / 2, h * 0.69, Graphics.FONT_XTINY, "Press START", c);
        }

        // My stats
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.82, Graphics.FONT_SMALL,
            "G " + game.goals + "   A " + game.assists, c);
    }
}

// Match time with a small stopwatch icon to its left, centred together on cx.
function drawMatchClock(dc, cx, cy, text) {
    var font = Graphics.FONT_MEDIUM;
    var r = dc.getFontHeight(font) * 0.22;  // stopwatch radius
    var gap = r * 0.8;
    var textW = dc.getTextWidthInPixels(text, font);
    var left = cx - (2 * r + gap + textW) / 2;
    var ix = left + r;
    var iy = cy + r * 0.15;

    dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
    dc.setPenWidth(2);
    dc.drawCircle(ix, iy, r);
    dc.drawLine(ix, iy, ix, iy - r * 0.6);         // hand
    dc.drawLine(ix, iy, ix + r * 0.45, iy);
    dc.setPenWidth(1);
    dc.fillRectangle(ix - r * 0.3, iy - r * 1.45, r * 0.6, r * 0.3);  // button
    dc.drawLine(ix, iy - r * 1.2, ix, iy - r);

    dc.drawText(left + 2 * r + gap, cy, font, text,
        Graphics.TEXT_JUSTIFY_LEFT | Graphics.TEXT_JUSTIFY_VCENTER);
}

// UP = us +1, DOWN = them +1, START (or BACK) = menu.
// Tap the green score = us +1, tap the red score = them +1.
// Plain InputDelegate (not BehaviorDelegate), so a tap isn't turned into "select".
class GameDelegate extends WatchUi.InputDelegate {
    function initialize() {
        InputDelegate.initialize();
    }

    function onKey(evt) {
        var key = evt.getKey();
        var game = getGame();
        // First START press kicks off the match.
        if (!game.isStarted() && key == WatchUi.KEY_ENTER) {
            game.start();
            if (Attention has :vibrate) {
                Attention.vibrate([new Attention.VibeProfile(100, 400)]);
            }
            WatchUi.requestUpdate();
            return true;
        }
        if (key == WatchUi.KEY_UP) { return bump(:us); }
        if (key == WatchUi.KEY_DOWN) { return bump(:them); }
        // START, or BACK, so a stray press doesn't end the match.
        if (key == WatchUi.KEY_ENTER || key == WatchUi.KEY_ESC || key == WatchUi.KEY_MENU) {
            openMenu();
            return true;
        }
        return false;
    }

    function onTap(evt) {
        var xy = evt.getCoordinates();
        var screen = System.getDeviceSettings();
        var y = xy[1].toFloat() / screen.screenHeight;
        if (y > 0.33 && y < 0.67) {
            return bump(xy[0] < screen.screenWidth / 2 ? :us : :them);
        }
        return true;  // ignore taps elsewhere
    }

    // Ignore swipes so a brushed screen can't change the score.
    function onSwipe(evt) { return true; }
}

var lastBumpMs = null;

// Add a point/goal/assist. Ignored if anything was added less than a second ago,
// so a double tap or double press can't count twice.
function bump(what) {
    // No scoring before the match starts.
    if (!getGame().isStarted()) {
        return true;
    }
    var now = System.getTimer();
    if (lastBumpMs != null && now - lastBumpMs < 1000) {
        return true;
    }
    lastBumpMs = now;
    getGame().add(what);
    if (Attention has :vibrate) {
        Attention.vibrate([new Attention.VibeProfile(70, 150)]);
    }
    WatchUi.requestUpdate();
    return true;
}

function openMenu() {
    var menu = new WatchUi.Menu2({ :title => "Me" });
    menu.addItem(new WatchUi.MenuItem("My goal", null, :goal, null));
    menu.addItem(new WatchUi.MenuItem("My assist", null, :assist, null));
    menu.addItem(new WatchUi.MenuItem("Undo last", null, :undo, null));
    menu.addItem(new WatchUi.MenuItem("End match", null, :exit, null));
    menu.addItem(new WatchUi.MenuItem("How to use", null, :help, null));
    WatchUi.pushView(menu, new MenuDelegate(), WatchUi.SLIDE_UP);
}

class MenuDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item) {
        var id = item.getId();
        if (id == :exit) {
            WatchUi.switchToView(new EndView(getGame()), new EndDelegate(), WatchUi.SLIDE_UP);
            return;
        }
        if (id == :help) {
            openHelp();
            return;
        }
        if (id == :undo) {
            getGame().undo();
        } else {
            bump(id);
        }
        WatchUi.popView(WatchUi.SLIDE_DOWN);
    }
}

// Short instructions, one per row; BACK returns to the menu.
function openHelp() {
    var menu = new WatchUi.Menu2({ :title => "How to use" });
    var rows = [
        ["START", "Start the match"],
        ["UP or tap green", "+1 my team"],
        ["DOWN or tap red", "+1 other team"],
        ["START or BACK", "Open the menu"],
        ["My goal / assist", "Also +1 my team"],
        ["Undo last", "Remove last entry"]
    ];
    for (var i = 0; i < rows.size(); i++) {
        menu.addItem(new WatchUi.MenuItem(rows[i][0], rows[i][1], i, null));
    }
    WatchUi.pushView(menu, new HelpDelegate(), WatchUi.SLIDE_LEFT);
}

class HelpDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item) {
    }
}
