# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes, merged with HSSwitch-specific instructions.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Project-Specific Guidelines (HSSwitch)

HSSwitch is a Windows audio-device-switcher tray app written in Python
(pycaw, pywebview, pystray, tkinter). Several fragile, already-solved
issues exist in this codebase — do not "fix" or "simplify" them without
being asked.

**Threading & environment constraints — never violate silently:**
- `pywebview` must run on the **main thread only**. Never call
  `webview.create_window()` or any webview API from a background thread,
  even if it looks like it would simplify the code.
- `pycaw` (COM-based) requires `CoInitialize()` / `CoUninitialize()` to be
  called explicitly in **every thread** that touches COM objects — this
  was already debugged once. Do not remove or "consolidate" these calls
  without checking each thread's lifecycle first.
- `pystray` tray icon logic runs in its own thread/loop. Don't merge it
  with the tkinter mainloop or webview loop unless explicitly asked —
  they have separate event-loop requirements on Windows.

**Surgical-change reminders specific to this repo:**
- Audio-device enumeration/switching code (pycaw) is validated and
  working — treat it as load-bearing. Extend, don't rewrite.
- GUI (tkinter) and tray (pystray) and web view (pywebview) layers should
  stay separated as they are now. If a new feature seems to require
  merging them, flag the tradeoff and ask before doing it.
- This is a solo portfolio project intended to demonstrate clean,
  understandable code for a job search — prefer readable straightforward
  Python over clever abstractions, even more strictly than the default
  "Simplicity First" rule.

**Goal-driven execution for this repo:**
- For any bug fix touching COM/threading, the verification step must
  include manually noting "tested: does audio device switch correctly
  after app has been idle / after sleep-wake" since these are the classes
  of bugs that showed up before automated tests won't catch.
- For new features, prefer a short manual test checklist over skipping
  verification, since this project doesn't have a full automated test
  suite yet.

---

## Release Workflow (HSSwitch)

**Version bump policy — don't bump on every fix.**
- Multiple small fixes/features during a work session accumulate under the *current* `APP_VERSION` — do not bump `version.py` after each individual change.
- Only bump the version when the user explicitly says to release (e.g. "릴리즈하자", "다음 버전"). If the current version number was already published as a GitHub Release/tag, a new bump is required at that point (tags can't be reused) — bump by one patch number and proceed.
- After bumping, always update `version.json` (`version`, `md5`, `notes`) to match.

**Shell split — do not mix these up.**
- `git add` / `git commit` / `git push` → **git bash** (MINGW64).
- `.\build.bat` and `Get-FileHash ... -Algorithm MD5` → **PowerShell** (`Get-FileHash` is PowerShell-only; running it in git bash silently does nothing).
- Order between "push source to git" and "run build.bat" doesn't functionally matter — `build.bat` builds from whatever is on local disk, not from git state. Recommend pushing source first only for keeping repo/build in sync, not because it's required.

**Standard release sequence:**
1. Make code changes.
2. When the user says to release: bump `version.py`.
3. Tell the user the exact git bash commands (add the changed files + `version.py`, commit, push to `main`) and the exact PowerShell commands (`cd` to repo, `.\build.bat`, `Get-FileHash dist\HSSwitch.zip -Algorithm MD5`).
4. Wait for the user to report the MD5 hash back.
5. Update `version.json` with the new version/hash/notes.
6. Give the user release info in this exact three-part format so they can paste it straight into GitHub's "New release" page:
   - **태그**: `vX.Y.Z`
   - **타이틀**: `HSSwitch vX.Y.Z`
   - **릴리즈 노트**: a short plain-language (Korean) summary of what changed, in a fenced code block.
7. Remind the user to attach `dist\HSSwitch.zip` (filename must stay exactly `HSSwitch.zip` — the update URL is a fixed `releases/latest/download/HSSwitch.zip` link) and to **Publish** the release, not leave it as Draft.
8. After both the GitHub Release is published and `version.json` is pushed, tell the user to wait ~5 minutes (raw.githubusercontent.com / CDN caching lag) before testing the in-app "업데이트 확인" flow on an older running instance.

**Known GitHub Release UI quirk:** publishing a Draft release can sometimes throw a spurious "tag name has already been taken" error. Workaround: bump to the next tag number and republish, or refresh and retry — don't spend time debugging this on GitHub's side.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
