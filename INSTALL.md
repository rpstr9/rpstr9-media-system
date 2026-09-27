# Install or use directly

For interactive use, open the complete master and selected workflow bundle in a capable assistant. A plain reading bundle needs no Python setup. The external strategy/identity methods still need to be available in full when requested.

For Codex, install the complete library and link its individual skills into your personal skill directory. Keeping shared references beside the skills is required; copying SKILL.md alone is incomplete. The installer refuses conflicting existing skills and changes no model, account or service settings.

```text
python3 scripts/install_skills.py --library-dest YOUR_PRIVATE_LIBRARY_DIRECTORY --skill-root YOUR_CODEX_SKILL_DIRECTORY
```

Use a version-specific library destination outside this source tree. The command verifies the supplied release manifest before copying. Newly installed skills become available when the host refreshes its skill inventory; open a new chat if this chat still lists the previous inventory. Begin with media-master, or invoke a specialist directly for a narrow task.

The optional private timer is a separate setup described in runtime/reference/README.md. Installing the methods does not configure an AI provider, authorize publishing or start recurring work.
