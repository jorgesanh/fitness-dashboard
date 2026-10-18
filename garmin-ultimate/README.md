# Ultimate Score — Garmin watch app

A Connect IQ watch app for ultimate frisbee. It tracks the game score, plus **your own** goals and assists, and records the game as an activity, so heart rate, time and calories still get logged.

## Controls (5-button watches like Fenix, Forerunner and Epix)

| Button | Action |
|---|---|
| **UP** | We scored → choose **Teammate** / **My goal** / **My assist** |
| **DOWN** | They scored (instant, double buzz) |
| **START** or **BACK** | Game menu: Resume · Undo · Pause clock · End & save · Season stats · Discard |

On touch watches (Venu, Vivoactive), swipe instead of pressing UP/DOWN.

- A goal or assist by you also adds a point to your team, so you never log the same point twice.
- **Undo** removes whatever you logged last. The menu shows what that was.
- BACK opens the menu instead of exiting, so a stray press mid-point can't kill the game.
- If the app closes mid-game, the score comes back the next time you open it.

## What gets saved

- **Garmin Connect:** an activity called "Ultimate" with HR and time. Its summary shows *Our score, Their score, My goals, My assists*.
- **On the watch:** *Season stats* shows W/L, total goals and assists, and G+A per game over your last 50 games.

## Install on your watch (one-time setup, ~15 min)

1. Install [VS Code](https://code.visualstudio.com/) and the **Monkey C** extension (Garmin).
2. Install the [Connect IQ SDK Manager](https://developer.garmin.com/connect-iq/sdk/), download the latest SDK, and download the device for your watch.
3. In VS Code run **Monkey C: Verify Installation**. It offers to create a developer key.
4. Open this `garmin-ultimate` folder. If your watch isn't in `manifest.xml`, run **Monkey C: Edit Products** and tick it.
5. Test in the simulator with **Run → Run Without Debugging**.
6. Run **Monkey C: Build for Device**, pick your watch, and you get a `.prg` file.
7. Plug in the watch over USB and copy the `.prg` into `GARMIN/APPS/`. Unplug the watch. "Ultimate Score" now shows up in your activities/apps list.
