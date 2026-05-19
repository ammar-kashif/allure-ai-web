# Meeting-bot patches

Local modifications to `moawizbinyamin/meeting-bot` that the Allure POC depends on. These exist because we found behavior we needed to change but didn't want to fork the bot outright.

## `meetui-participant-exit.patch`

**What it does.** Three independent fixes to the simple Google Meet bot:

1. **Participant-count exit (meetUi.ts)** — adds a fallback "leave when all participants are gone" trigger to `waitUntilMeetingEnds`. The loop now counts `<audio>` elements on the Google Meet page (each remote participant contributes one; the muted bot contributes none). If the count is `0` for 3 consecutive polls (≈ 9 s), the bot exits cleanly. This is belt-and-suspenders for cases where the older text/URL detection misses.
2. **Detached-Frame recovery (GoogleMeetSimpleBot.ts)** — wraps `audioCapture.stop()` and `screenRecorder.stop()` in try/catch. When Meet navigates away from the meeting URL before the bot's post-end cleanup runs, `page.evaluate` throws `Attempted to use detached Frame`, the exception escapes the post-end block, and `finalizeAudioRecording` never runs — losing the entire recording (this has cost us multiple POC runs). The MediaRecorder's data is already flushed to disk by then, so swallowing the stop error and letting finalize run on the existing `.tmp.webm` recovers the recording.
3. **Less-loose text-match (meetUi.ts)** — removes `"no one else is here"` from the end-of-meeting phrase list. Meet renders that string transiently during normal participant churn and was firing false positives that, combined with bug #2, lost recordings entirely.

Plus a debug log line in `waitUntilMeetingEnds` that fires whenever the audio-element count changes, so future runs are easy to diagnose without re-instrumenting.

**How to apply on a fresh bot clone.**

```bash
cd ~/meeting-bot
git apply /Users/zainabbas/Programming/Allure/allure-ai-web/bot-patches/meetui-participant-exit.patch
```

`nodemon` watches `src/**` so the change reloads automatically; no restart needed if the bot is already running.

**Verifying it took effect.** Dispatch a meeting, admit the bot, then **leave the meeting yourself** without ending it for everyone. Within ~10 s of becoming the sole remaining participant the bot should log:

```
No remote audio streams for 9s — all participants left
Stopping recording { endReason: 'ended' }
```

and the `.mp3` should appear in the recordings dir.

**Why a patch and not a fork.** The bot is upstream-maintained third-party code. A patch file keeps the modification small, reviewable, and easy to drop if upstream adds equivalent logic.
