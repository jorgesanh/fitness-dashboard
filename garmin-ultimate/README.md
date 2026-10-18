# Ultimate Score — Garmin watch app

One screen, nothing else:

```
        14:32          ← time of day
        23:41          ← match time (starts when you open the app)
     7        5        ← us (green)   them (red)
      Point 1:12       ← time since the last point was added (resets to 0:00)
      G 2   A 3        ← my goals / assists
```

## Buttons

| Button | Does |
|---|---|
| **UP** | +1 us |
| **DOWN** | +1 them |
| **START** (or BACK) | My goal · My assist · Undo last · End match |

Goals/assists are just your personal count — they don't change the team score. When you score, press UP **and** log "My goal".

## Install on your watch

1. Install [VS Code](https://code.visualstudio.com/) + the **Monkey C** extension.
2. Install the [Connect IQ SDK Manager](https://developer.garmin.com/connect-iq/sdk/), download the latest SDK and your watch's device.
3. In VS Code: **Monkey C: Verify Installation** (creates a developer key).
4. Open this `garmin-ultimate` folder. If your watch isn't listed in `manifest.xml`, run **Monkey C: Edit Products** and tick it.
5. **Monkey C: Build for Device** → pick your watch → you get a `.prg` file.
6. Plug the watch in by USB, copy the `.prg` into `GARMIN/APPS/`, unplug. Open "Ultimate Score" from your apps list.
