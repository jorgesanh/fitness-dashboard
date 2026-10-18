import Toybox.Activity;
import Toybox.ActivityRecording;
import Toybox.Application;
import Toybox.Attention;
import Toybox.FitContributor;
import Toybox.Lang;
import Toybox.Time;

// Every scoring action is one event, so undo is just "drop the last event".
enum {
    EV_TEAMMATE, // our team scored, I wasn't involved
    EV_GOAL,     // our team scored, I caught it
    EV_ASSIST,   // our team scored, I threw it
    EV_THEM      // they scored
}

const MAX_HISTORY = 50;

// Score state + the FIT recording session for one game.
class Game {
    var events = [];
    var session = null;

    hidden var _fUs = null;
    hidden var _fThem = null;
    hidden var _fGoals = null;
    hidden var _fAssists = null;

    function initialize() {
        // Recover score if the app was closed or crashed mid-game.
        var saved = Application.Storage.getValue("live");
        if (saved instanceof Array) {
            events = saved;
        }
        startRecording();
    }

    // --- Score ---------------------------------------------------------

    function us() { return count(EV_TEAMMATE) + count(EV_GOAL) + count(EV_ASSIST); }
    function them() { return count(EV_THEM); }
    function goals() { return count(EV_GOAL); }
    function assists() { return count(EV_ASSIST); }

    hidden function count(ev) {
        var n = 0;
        for (var i = 0; i < events.size(); i++) {
            if (events[i] == ev) { n++; }
        }
        return n;
    }

    function add(ev) {
        events.add(ev);
        changed();
        // Distinct buzz patterns so you can confirm without looking.
        if (ev == EV_THEM) {
            vibrate([new Attention.VibeProfile(60, 120), new Attention.VibeProfile(0, 120), new Attention.VibeProfile(60, 120)]);
        } else {
            vibrate([new Attention.VibeProfile(80, 250)]);
        }
    }

    function undo() {
        if (events.size() > 0) {
            events = events.slice(0, events.size() - 1);
            changed();
            vibrate([new Attention.VibeProfile(40, 80)]);
        }
    }

    function lastEventLabel() {
        if (events.size() == 0) { return null; }
        return eventLabel(events[events.size() - 1]);
    }

    hidden function changed() {
        Application.Storage.setValue("live", events);
        if (_fUs != null) {
            _fUs.setData(us());
            _fThem.setData(them());
            _fGoals.setData(goals());
            _fAssists.setData(assists());
        }
    }

    hidden function vibrate(pattern) {
        if (Attention has :vibrate) {
            Attention.vibrate(pattern);
        }
    }

    // --- Recording -----------------------------------------------------

    hidden function startRecording() {
        if (!(Toybox has :ActivityRecording)) { return; }
        session = ActivityRecording.createSession({
            :name => "Ultimate",
            :sport => Activity.SPORT_GENERIC
        });
        var opts = { :mesgType => FitContributor.MESG_TYPE_SESSION, :units => "pts" };
        _fUs = session.createField("team_score", 0, FitContributor.DATA_TYPE_UINT8, opts);
        _fThem = session.createField("opponent_score", 1, FitContributor.DATA_TYPE_UINT8, opts);
        _fGoals = session.createField("my_goals", 2, FitContributor.DATA_TYPE_UINT8, opts);
        _fAssists = session.createField("my_assists", 3, FitContributor.DATA_TYPE_UINT8, opts);
        changed();
        session.start();
    }

    function isRecording() {
        return session != null && session.isRecording();
    }

    function togglePause() {
        if (session == null) { return; }
        if (session.isRecording()) {
            session.stop();
        } else {
            session.start();
        }
    }

    // Elapsed (pause-aware) game time in ms.
    function elapsedMs() {
        var info = Activity.getActivityInfo();
        if (info != null && info.timerTime != null) { return info.timerTime; }
        return 0;
    }

    function heartRate() {
        var info = Activity.getActivityInfo();
        return info != null ? info.currentHeartRate : null;
    }

    // --- End of game ---------------------------------------------------

    function save() {
        if (session != null) {
            if (session.isRecording()) { session.stop(); }
            session.save();
            session = null;
        }
        var history = Application.Storage.getValue("history");
        if (!(history instanceof Array)) { history = []; }
        history.add({
            "t" => Time.now().value(),
            "us" => us(),
            "them" => them(),
            "g" => goals(),
            "a" => assists()
        });
        if (history.size() > MAX_HISTORY) {
            history = history.slice(history.size() - MAX_HISTORY, null);
        }
        Application.Storage.setValue("history", history);
        Application.Storage.deleteValue("live");
    }

    function discard() {
        if (session != null) {
            if (session.isRecording()) { session.stop(); }
            session.discard();
            session = null;
        }
        Application.Storage.deleteValue("live");
    }
}

function eventLabel(ev) {
    if (ev == EV_GOAL) { return "My goal"; }
    if (ev == EV_ASSIST) { return "My assist"; }
    if (ev == EV_THEM) { return "Their point"; }
    return "Our point";
}

function formatDuration(ms) {
    var s = ms / 1000;
    var h = s / 3600;
    var m = (s % 3600) / 60;
    s = s % 60;
    if (h > 0) {
        return h.format("%d") + ":" + m.format("%02d") + ":" + s.format("%02d");
    }
    return m.format("%d") + ":" + s.format("%02d");
}
