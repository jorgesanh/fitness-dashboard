import Toybox.Lang;
import Toybox.System;
import Toybox.WatchUi;

// UP   = we scored (then pick: teammate / my goal / my assist)
// DOWN = they scored
// START or BACK = game menu (BACK never exits by accident mid-game)
class GameDelegate extends WatchUi.BehaviorDelegate {
    function initialize() {
        BehaviorDelegate.initialize();
    }

    function onPreviousPage() {
        var menu = new WatchUi.Menu2({ :title => "We scored!" });
        menu.addItem(new WatchUi.MenuItem("Teammate", null, :teammate, null));
        menu.addItem(new WatchUi.MenuItem("My goal", "I caught it", :goal, null));
        menu.addItem(new WatchUi.MenuItem("My assist", "I threw it", :assist, null));
        WatchUi.pushView(menu, new ScoredMenuDelegate(), WatchUi.SLIDE_UP);
        return true;
    }

    function onNextPage() {
        getGame().add(EV_THEM);
        WatchUi.requestUpdate();
        return true;
    }

    function onSelect() {
        openGameMenu();
        return true;
    }

    function onMenu() {
        openGameMenu();
        return true;
    }

    function onBack() {
        openGameMenu();
        return true;
    }
}

class ScoredMenuDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item) {
        var id = item.getId();
        var ev = EV_TEAMMATE;
        if (id == :goal) { ev = EV_GOAL; }
        else if (id == :assist) { ev = EV_ASSIST; }
        getGame().add(ev);
        WatchUi.popView(WatchUi.SLIDE_DOWN);
    }
}

function openGameMenu() {
    var game = getGame();
    var menu = new WatchUi.Menu2({ :title => game.us().toString() + " - " + game.them().toString() });
    menu.addItem(new WatchUi.MenuItem("Resume game", null, :back, null));
    var last = game.lastEventLabel();
    if (last != null) {
        menu.addItem(new WatchUi.MenuItem("Undo", last, :undo, null));
    }
    menu.addItem(new WatchUi.MenuItem(game.isRecording() ? "Pause clock" : "Start clock", null, :pause, null));
    menu.addItem(new WatchUi.MenuItem("End & save", null, :save, null));
    menu.addItem(new WatchUi.MenuItem("Season stats", null, :stats, null));
    menu.addItem(new WatchUi.MenuItem("Discard game", null, :discard, null));
    WatchUi.pushView(menu, new GameMenuDelegate(), WatchUi.SLIDE_UP);
}

class GameMenuDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item) {
        var id = item.getId();
        var game = getGame();
        if (id == :back) {
            WatchUi.popView(WatchUi.SLIDE_DOWN);
        } else if (id == :undo) {
            game.undo();
            WatchUi.popView(WatchUi.SLIDE_DOWN);
        } else if (id == :pause) {
            game.togglePause();
            WatchUi.popView(WatchUi.SLIDE_DOWN);
        } else if (id == :save) {
            var summary = new SummaryView(game.us(), game.them(), game.goals(), game.assists());
            game.save();
            WatchUi.switchToView(summary, new ExitDelegate(), WatchUi.SLIDE_UP);
        } else if (id == :stats) {
            WatchUi.pushView(new StatsView(), new WatchUi.BehaviorDelegate(), WatchUi.SLIDE_LEFT);
        } else if (id == :discard) {
            WatchUi.pushView(new WatchUi.Confirmation("Discard this game?"),
                new DiscardDelegate(), WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

class DiscardDelegate extends WatchUi.ConfirmationDelegate {
    function initialize() {
        ConfirmationDelegate.initialize();
    }

    function onResponse(response) {
        if (response == WatchUi.CONFIRM_YES) {
            getGame().discard();
            System.exit();
        }
        return true;
    }
}

// Any button on the final summary closes the app.
class ExitDelegate extends WatchUi.BehaviorDelegate {
    function initialize() {
        BehaviorDelegate.initialize();
    }

    function onSelect() { System.exit(); return true; }
    function onBack() { System.exit(); return true; }
}
