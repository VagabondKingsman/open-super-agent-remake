# Grok Bot / Build Bot compatibility

- Load sibling skills with the Skill tool by name.
- When the user names a skill or flow, follow that flow exactly.
- Repo code changes for open-super-agent-remake go through CloudAgent (`code-changes`). Local `/workspace/open-super-agent` is for read/verify/smoke.
- Package mirror: `/workspace/ai-native-skills/<name>/` (same content as this skill directory).
- `SKILL_DIR` for scripts = this directory or the workspace mirror. Prefer workspace mirror for writes/runs.
- Compose with Cursor-managed skills; do not replace them.
- Multi-step: print `Skill Flow: A -> B -> C` at the start.
