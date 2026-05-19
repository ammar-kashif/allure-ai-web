# Meeting-bot patches

Local modifications to `moawizbinyamin/meeting-bot` that the Allure POC depends on. These exist because we found behavior we needed to change but didn't want to fork the bot outright.

## `meetui-participant-exit.patch`

**What it does.** Adds a "leave when all participants are gone" trigger to the bot's meeting-end loop in `src/simple/meetUi.ts`. The loop now counts `<audio>` elements on the Google Meet page (each remote participant contributes one; the bot itself is muted and contributes none). If the count is `0` for 3 consecutive polls (≈ 9 s), the bot exits cleanly with `endReason: 'ended'` and the recording is finalized normally.

**Also.** Removes `"no one else is here"` from the text-match list. Meet renders that string transiently in normal operation (during participant joins/leaves, brief tab refocus, network blips), and it was firing a false-positive end-of-meeting in long calls — costing us the entire first recording in one POC run because the bot then retried and the original `.tmp.webm` finalization crashed with a detached Frame error.

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
