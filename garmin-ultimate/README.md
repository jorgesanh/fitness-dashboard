# Ultimate Score — Garmin watch app

One screen, nothing else:

```
        14:32          ← time of day
        23:41          ← match time (starts when you open the app)
     7        5        ← us (green)   them (red)
      Point 1:12       ← time since the last point was added (resets to 0:00)
      G 2   A 3        ← my goals / assists (tap to add)
```

## Buttons

| Button | Does |
|---|---|
| **UP** | +1 us |
| **DOWN** | +1 them |
| **START** (or BACK) | My goal · My assist · Undo last · End match |

| **Tap G** (bottom left of screen) | My goal |
| **Tap A** (bottom right of screen) | My assist |

"My goal" and "My assist" also add a point to your team, so don't press UP as well. Use UP only when a teammate scores without you. Swipes are ignored, so brushing the screen can't change the score.

## Install on your watch

1. Install [VS Code](https://code.visualstudio.com/) + the **Monkey C** extension.
2. Install the [Connect IQ SDK Manager](https://developer.garmin.com/connect-iq/sdk/), download the latest SDK and your watch's device.
3. In VS Code: **Monkey C: Verify Installation** (creates a developer key).
4. Open this `garmin-ultimate` folder. If your watch isn't listed in `manifest.xml`, run **Monkey C: Edit Products** and tick it.
5. **Monkey C: Build for Device** → pick your watch → you get a `.prg` file.
6. Plug the watch in by USB, copy the `.prg` into `GARMIN/APPS/`, unplug. Open "Ultimate Score" from your apps list.
