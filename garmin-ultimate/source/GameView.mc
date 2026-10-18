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
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.25, Graphics.FONT_MEDIUM, game.matchTime(), c);

        // Score: us green, them red
        dc.setColor(Graphics.COLOR_GREEN, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.3, h * 0.5, Graphics.FONT_NUMBER_HOT, game.us.toString(), c);
        dc.setColor(Graphics.COLOR_RED, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w * 0.7, h * 0.5, Graphics.FONT_NUMBER_HOT, game.them.toString(), c);

        // Time since last point
        dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.69, Graphics.FONT_XTINY, "Point " + game.pointTime(), c);

        // My stats
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        dc.drawText(w / 2, h * 0.82, Graphics.FONT_SMALL,
            "G " + game.goals + "   A " + game.assists, c);
    }
}

// UP = us +1, DOWN = them +1, START (or BACK) = menu
class GameDelegate extends WatchUi.BehaviorDelegate {
    function initialize() {
        BehaviorDelegate.initialize();
    }

    function onPreviousPage() { return bump(:us); }
    function onNextPage() { return bump(:them); }
    function onSelect() { openMenu(); return true; }
    function onMenu() { openMenu(); return true; }
    // BACK opens the menu so a stray press doesn't end the match.
    function onBack() { openMenu(); return true; }
}

function bump(what) {
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
    WatchUi.pushView(menu, new MenuDelegate(), WatchUi.SLIDE_UP);
}

class MenuDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item) {
        var id = item.getId();
        if (id == :exit) {
            System.exit();
        }
        if (id == :undo) {
            getGame().undo();
        } else {
            bump(id);
        }
        WatchUi.popView(WatchUi.SLIDE_DOWN);
    }
}
