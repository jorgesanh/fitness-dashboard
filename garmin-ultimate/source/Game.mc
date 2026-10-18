import Toybox.Lang;
import Toybox.System;

// The whole match: four counters and a start time.
class Game {
    var us = 0;
    var them = 0;
    var goals = 0;
    var assists = 0;

    hidden var _startMs;
    hidden var _last = [];  // names of changed counters, newest last, for undo

    function initialize() {
        _startMs = System.getTimer();
    }

    function add(what) {
        if (what == :us) { us++; }
        else if (what == :them) { them++; }
        else if (what == :goal) { goals++; }
        else if (what == :assist) { assists++; }
        _last.add(what);
    }

    function undo() {
        if (_last.size() == 0) { return; }
        var what = _last[_last.size() - 1];
        _last = _last.slice(0, _last.size() - 1);
        if (what == :us) { us--; }
        else if (what == :them) { them--; }
        else if (what == :goal) { goals--; }
        else if (what == :assist) { assists--; }
    }

    // Match clock as m:ss (or h:mm:ss).
    function matchTime() {
        var s = (System.getTimer() - _startMs) / 1000;
        var h = s / 3600;
        var m = (s % 3600) / 60;
        s = s % 60;
        if (h > 0) {
            return h.format("%d") + ":" + m.format("%02d") + ":" + s.format("%02d");
        }
        return m.format("%d") + ":" + s.format("%02d");
    }
}
