import Toybox.Lang;
import Toybox.System;

// The whole match: four counters and a start time.
class Game {
    var us = 0;
    var them = 0;
    var goals = 0;
    var assists = 0;

    hidden var _startMs = null;  // null until START is pressed
    hidden var _last = [];  // names of changed counters, newest last, for undo
    hidden var _pointTimes = [];  // when each team point was added, for the point clock

    function initialize() {
    }

    function start() {
        _startMs = System.getTimer();
    }

    function isStarted() {
        return _startMs != null;
    }

    function add(what) {
        // My goal or assist is also a point for us.
        if (what == :us) { us++; }
        else if (what == :them) { them++; }
        else if (what == :goal) { goals++; us++; }
        else if (what == :assist) { assists++; us++; }
        _last.add(what);
        _pointTimes.add(System.getTimer());
    }

    function undo() {
        if (_last.size() == 0) { return; }
        var what = _last[_last.size() - 1];
        _last = _last.slice(0, _last.size() - 1);
        _pointTimes = _pointTimes.slice(0, _pointTimes.size() - 1);
        if (what == :us) { us--; }
        else if (what == :them) { them--; }
        else if (what == :goal) { goals--; us--; }
        else if (what == :assist) { assists--; us--; }
    }

    function matchTime() {
        return isStarted() ? formatTime(System.getTimer() - _startMs) : "0:00";
    }

    // Time since the last team point (or since kickoff), so you can see a point registered.
    function pointTime() {
        if (!isStarted()) { return "0:00"; }
        var since = _pointTimes.size() > 0 ? _pointTimes[_pointTimes.size() - 1] : _startMs;
        return formatTime(System.getTimer() - since);
    }
}

// m:ss (or h:mm:ss)
function formatTime(ms) {
    var s = ms / 1000;
    var h = s / 3600;
    var m = (s % 3600) / 60;
    s = s % 60;
    if (h > 0) {
        return h.format("%d") + ":" + m.format("%02d") + ":" + s.format("%02d");
    }
    return m.format("%d") + ":" + s.format("%02d");
}
