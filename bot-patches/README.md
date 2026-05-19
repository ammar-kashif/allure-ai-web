# Meeting-bot patches

Local modifications to `moawizbinyamin/meeting-bot` that the Allure POC depends on. These exist because we found behavior we needed to change but didn't want to fork the bot outright.

## `meetui-participant-exit.patch`

**What it does.** Three independent fixes to the simple Google Meet bot:

1. **Participant-count exit (meetUi.ts)** — adds a fallback "leave when all participants are gone" trigger to `waitUntilMeetingEnds`. The loop counts `[data-participant-id]` elements (Meet renders one per participant, including the bot). When the count drops to `1` (only the bot remains) for 3 consecutive polls (≈ 9 s), the bot exits cleanly. Three corroborating signals are gathered each poll — `<audio>` total, live-MediaStream-track count, and `[data-allocation-index]` video tiles — and logged on change as `Meet signal change: p=N v=N a=N aLive=N call=true|false` for easy diagnosis. An earlier version counted `<audio>` nodes directly; that was discarded after live testing showed Meet keeps stale `<audio>` elements long after participants leave.
2. **Detached-Frame recovery (GoogleMeetSimpleBot.ts)** — wraps `audioCapture.stop()` and `screenRecorder.stop()` in try/catch. When Meet navigates away from the meeting URL before the bot's post-end cleanup runs, `page.evaluate` throws `Attempted to use detached Frame`, the exception escapes the post-end block, and `finalizeAudioRecording` never runs — losing the entire recording (this cost us multiple POC runs). The MediaRecorder's data is already flushed to disk by then, so swallowing the stop error and letting finalize run on the existing `.tmp.webm` recovers the recording.
3. **Less-loose text-match (meetUi.ts)** — removes `"no one else is here"` from the end-of-meeting phrase list. Meet renders that string transiently during normal participant churn and was firing false positives that, combined with bug #2, lost recordings entirely.

**How to apply on a fresh bot clone.**

```bash
cd ~/meeting-bot
git apply /Users/zainabbas/Programming/Allure/allure-ai-web/bot-patches/meetui-participant-exit.patch
```

`nodemon` watches `src/**` so the change reloads automatically; no restart needed if the bot is already running.

**Verifying it took effect.** Dispatch a meeting, admit the bot, then **leave the meeting yourself** without ending it for everyone. Within ~10 s of becoming the sole remaining participant the bot should log:

```
Meet signal change: p=1 v=1 a=N aLive=0 call=true
Only the bot remains in the participant list for 9s — exiting
Stopping recording { endReason: 'ended' }
```

and the `.mp3` should appear in the recordings dir.

**Why a patch and not a fork.** The bot is upstream-maintained third-party code. A patch file keeps the modification small, reviewable, and easy to drop if upstream adds equivalent logic.
