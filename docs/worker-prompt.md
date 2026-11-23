# Worker contract (sub-session prompt) for vtt-transcribe

Copy this into a sub-session's prompt, fill in the task block, and point the session at this file. The rules in `CLAUDE.md`
apply in full; this document is the contract between coordinator and worker.

---

## Task

- **Bead:** `{TASK_ID}` (`cd /home/vetch101/code/JLCodeSource/vtt-beads && bd show {TASK_ID}`)
- **Repo and branch:** `vtt-transcribe`, branch `{BRANCH}`, cut from the latest `main`.
- **Goal:** {ONE_SENTENCE_GOAL}
- **Acceptance criteria** (each one is verified by a test or an explicit check):
  1. {CRITERION_1}
  2. {CRITERION_2}
- **You own these files/areas only:** {FILES_OR_AREAS}
- **Running in parallel with you (do not touch their areas):** {OTHER_WORKERS_AND_THEIR_AREAS}
- **Out of scope:** everything else. Do not widen your own scope.

## How you work

1. Read `CLAUDE.md` and the bead. Mark the bead `in_progress`.
2. Work in strict red, green, refactor commits (`CLAUDE.md` section 1): a `test:` commit with the failure output in the body, a
   `feat:`/`fix:` commit with the smallest change, a `refactor:` commit. Never skip the refactor: if your code needs nothing,
   refactor more widely in its own commit. Several small cycles beat one big one.
3. Never weaken, skip or delete a test to get green. A genuinely wrong test gets its own `test:` commit with evidence.
4. Out-of-scope findings (bugs, gaps, ideas, wider refactorings) become new beads with `discovered-from:{TASK_ID}` and go in
   your report. You do not fix them.
5. Blocked? Write down why (in the bead and in your report) and stop. Never guess or work around a blocker.
6. Finish by running **all** checks from `CLAUDE.md` section 3, rebasing onto the latest `main`, re-running the checks, and
   pushing your branch. Open a PR if the coordinator asked for one. Do not merge unless told to. Do not tag, release,
   publish or deploy.

## Your report (end of every task)

- **Task ID** and **outcome:** `done` or `blocked` (with the reason).
- **Commits:** the list, in order, with their subjects.
- **Tests added** and where, and the checks you ran with their results (say plainly what you could not run).
- **New issues found:** the follow-on bead IDs.

## Closing down

After the report, complete `CLAUDE.md` section 6: close off what is necessary, raise follow-on beads (improvements and wider
refactorings), `bd dolt push`, tell the coordinator you are ready for archival, and wait. **Do not archive the session
yourself.** The coordinator asks the user, and archives only with approval.

*Canonical copy: `vtt-transcribe-server/docs/worker-prompt.md`. Copies in the other vtt repos differ only in the repo name.*
