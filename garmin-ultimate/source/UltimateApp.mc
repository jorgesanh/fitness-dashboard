import Toybox.Application;
import Toybox.Lang;
import Toybox.WatchUi;

class UltimateApp extends Application.AppBase {
    var game = null;

    function initialize() {
        AppBase.initialize();
    }

    function onStart(state) {
        game = new Game();
    }

    function getInitialView() {
        return [new GameView(), new GameDelegate()];
    }
}

function getGame() {
    return (Application.getApp() as UltimateApp).game;
}
