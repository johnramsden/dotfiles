# Global Behavioral Instructions

## Git Push — NEVER

- NEVER run `git push` (or any equivalent: `gh pr create`, `gh pr merge`,
  force-push, tag push, `git push --delete`) on the user's behalf.
- "Try it on the branch", "test it in CI", "apply the fix" do NOT mean push.
  Commit locally, stop, and tell the user the push command to run.
- The ONLY exception is an explicit instruction in the current message
  containing the word "push" (e.g. "push it", "push to upstream"). A prior
  approval never carries over to a later push.

## Git Commits

- All commits must be signed (using GPG or SSH signing as configured in git).
- All commits must include a `Signed-off-by` trailer.
- Retrieve the user's name and email from `git config user.name` and `git config user.email` to construct the sign-off line.
- Claude should always use `Assisted-By` trailer, not `Co-Authored-By`
- The user's `Signed-off-by` should come after any `Co-Authored-By` or `Assisted-By`

## Build & Test Execution

- Before running builds or tests, always ask whether the user would like them run inside a virtual machine.
- If the user has not yet provided a VM location in this session, run `multipass info` (with no arguments) to check if the current project directory is mounted in a Multipass VM.
- If a mount matching the current project is found, offer to run the build/tests inside that VM via `multipass exec`.
- When using `multipass exec`, always pass `--working-directory` to set the correct path inside the VM, rather than relying on the shell profile to `cd` into the right directory.
- If no matching VM is found, proceed locally (or ask the user for a VM name).


## Explanations

- Lead with the answer in one or two sentences. Stop there unless asked.
- Hard cap: 6 sentences for a normal reply. Longer only on explicit request.
- No headers, tables, or bulleted breakdowns unless asked for them.
- Do not narrate verification, list what you ruled out, or restate the
  question. Report the result, not the journey.
- Corrections are one sentence. No post-mortems.

## Commit messages and changelogs

House style, per debian/changelog and the backport-* branches:

- Subject: `d/<file>: <What changed>.` Imperative, sentence case, ends
  with a period, under 72 chars.
- Body: at most two short sentences, and only if the subject is not
  self-explanatory. Most commits need none.
- References on their own line, full URL, never a bare hash or number:
  `Upstream commit: <url>` / `Bug: <url>`.
- Trailers last: `Assisted-By:` then the user's `Signed-off-by:`.
- Never include: verification notes, alternatives considered, mechanism
  walkthroughs, or restatements of the diff.
- Changelog bullets are one line, two at most. Same `d/<file>: <What>.`
  shape. One bullet per change; do not merge unrelated changes.
- One logical change per commit.

## References

- When referring to an upstream commit, bug or PR, always write the full URL,
  never a bare hash or number. Applies to commit messages, patch headers,
  changelogs and chat replies.
