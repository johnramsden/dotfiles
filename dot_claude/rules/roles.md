# Global Behavioral Instructions

## Git Commits

- All commits must be signed (using GPG or SSH signing as configured in git).
- All commits must include a `Signed-off-by` trailer.
- Retrieve the user's name and email from `git config user.name` and `git config user.email` to construct the sign-off line.
- The user's `Signed-off-by` should come after any `Co-Authored-By`

## Build & Test Execution

- Before running builds or tests, always ask whether the user would like them run inside a virtual machine.
- If the user has not yet provided a VM location in this session, run `multipass info` (with no arguments) to check if the current project directory is mounted in a Multipass VM.
- If a mount matching the current project is found, offer to run the build/tests inside that VM via `multipass exec`.
- When using `multipass exec`, always pass `--working-directory` to set the correct path inside the VM, rather than relying on the shell profile to `cd` into the right directory.
- If no matching VM is found, proceed locally (or ask the user for a VM name).

## Documentation and Planning Documents

- When asked to write an explanation document or a planning document, place it under `.claude/docs/` or `.claude/plan/` within the current project directory (not in the project's public docs tree).
- When asked to write a review to disk, place it under `.claude/reviews/` within the current project directory.
- Use Markdown format for these documents.
