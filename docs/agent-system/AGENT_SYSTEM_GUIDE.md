# AGENT_SYSTEM_GUIDE.md
## Kitchen Assistant — Installation and Usage Guide

**Status:** Usage guide  
**Audience:** Project owner and AI assistants  
**Important:** This package is a set of Markdown instructions and templates. Actual Agent discovery, Skills loading, and command execution depend on the AI platform.

---

## 1. What this system contains

The Agent System supports work on the Kitchen Assistant repository. It is separate from the product's frontend/backend source structure.

| File/folder | Purpose |
|---|---|
| `AGENTS.md` | Shared rules for AI work in this repository |
| `.agents/agents/` | Five role definitions |
| `.agents/skills/` | Six domain Skills already maintained by the project |
| `.agents/commands/` | Five reusable task prompt templates |
| `docs/agent-system/AGENT_WORKFLOW.md` | Role collaboration and handoff rules |
| `docs/agent-system/AGENT_SYSTEM_GUIDE.md` | This installation and usage guide |

Agent definitions and commands are Markdown files. They are not executable application code.

## 2. Expected repository placement

Merge the package into the existing repository without deleting or replacing product source files:

```text
kitchen-assistant/
├── AGENTS.md
├── .agents/
│   ├── agents/
│   │   ├── system-architect.md
│   │   ├── database-engineer.md
│   │   ├── backend-developer.md
│   │   ├── frontend-developer.md
│   │   └── qa-security-engineer.md
│   ├── skills/
│   │   ├── inventory-ledger/SKILL.md
│   │   ├── backend-module/SKILL.md
│   │   ├── frontend-responsive/SKILL.md
│   │   ├── document-ingestion/SKILL.md
│   │   ├── reports-and-assistant/SKILL.md
│   │   └── testing-and-git/SKILL.md
│   └── commands/
│       ├── project-check.md
│       ├── implement-module.md
│       ├── review-code.md
│       ├── run-tests.md
│       └── prepare-handoff.md
└── docs/
    └── agent-system/
        ├── AGENT_WORKFLOW.md
        └── AGENT_SYSTEM_GUIDE.md
```

This is an additive overlay on the Project Structure. Existing `frontend/`, `backend/`, `scripts/`, architecture documents, decisions, and other files remain in place.

## 3. Safe installation steps

1. Make a backup or commit the current repository state.
2. Copy the root `AGENTS.md` into the repository root. If one already exists, compare and merge; do not overwrite useful project-specific rules blindly.
3. Copy `.agents/agents/` into the existing `.agents/` directory.
4. Preserve the six existing `.agents/skills/` directories. Do not replace their contents with placeholders or similarly named files from another package.
5. Copy `.agents/commands/` into `.agents/commands/`.
6. Copy the two guide files into `docs/agent-system/`.
7. Inspect `git status` and confirm only intended files were added or changed.
8. Open a few files to confirm paths and text are intact.

Do not delete, rename, or move product source folders as part of installing the Agent System.

## 4. How to use the system with an AI platform

### 4.1 Platform with repository access and instruction discovery
If the platform supports repository access and recognizes `AGENTS.md`:
- Give it the repository.
- Ask it to read `AGENTS.md` first.
- Ask it to load only the relevant Agent definition and Skill for the task.
- Provide the relevant Command template or invoke the platform's supported mechanism if it has one.
- Require a file-level change summary and test evidence.

Do not assume that a platform automatically discovers `.agents/agents/`, `.agents/skills/`, or `.agents/commands/`. Check its documentation/configuration and test discovery with a small read-only task.

### 4.2 Web chat without repository or filesystem access
A web chat cannot inspect your local VS Code repository merely because these files exist on your computer.

For each task, provide the AI with:
1. `AGENTS.md`.
2. The relevant Agent definition.
3. The relevant Skill file(s).
4. The relevant Command template.
5. Relevant architecture/plan sections.
6. The exact source files or a project ZIP if the AI needs to inspect or edit code.

Ask it to return:
- A list of files inspected.
- Full contents of new/changed files or a patch/diff.
- Tests it actually ran and their outputs.
- Tests not run and why.
- Any unresolved decisions or blockers.

You then transfer returned files into the local repository and run/verify them in your environment.

### 4.3 Platform without true multi-agent execution
If the platform cannot start separate Agents, use the role definitions as sequential review perspectives in one conversation:
1. Architect perspective: define scope and contract.
2. Relevant implementation perspective: make the change.
3. QA & Security perspective: review and test.

This is role-based prompting, not proof that multiple autonomous Agents executed independently.

## 5. Recommended task recipe

For a typical implementation task:

1. Start with `.agents/commands/project-check.md` if repository state or scope is uncertain.
2. Provide the relevant sections of `AGENTS.md` and architecture documents.
3. Select one primary Agent role.
4. Provide only the Skill(s) relevant to the task.
5. Use `.agents/commands/implement-module.md`.
6. After implementation, use `.agents/commands/review-code.md`.
7. Use `.agents/commands/run-tests.md` for test execution.
8. Finish with `.agents/commands/prepare-handoff.md`.

For a documentation-only task, do not load backend/frontend Skills unnecessarily. For a frontend-only task, do not load the inventory-ledger Skill unless the task touches inventory-ledger behavior.

## 6. Example prompt for a web AI

Adapt this prompt and attach the named files:

> Read `AGENTS.md` first and follow it as the shared project policy. Use the attached Agent definition as your role, the attached Skill as the task-specific procedure, and the attached Command as the requested workflow. Use Architecture Revision 6.3 and the Implementation Plan as the governing technical references. Do not invent missing decisions or change frozen architecture. Inspect only the provided repository files. Before editing, state the task scope, affected files, and acceptance criteria. Then implement the smallest complete change. Return every changed file or a clear patch, exact tests run with observed results, tests not run, unresolved questions, and a handoff summary. Do not claim access to local files or test execution unless actually available.

## 7. Token-efficient context sharing

Do not attach every project document and every Skill to every task.

Use this selection:
- Always: `AGENTS.md` plus task description.
- Architecture: only relevant sections of Revision 6.3 and Implementation Plan.
- Agent: one primary role; add another only for a real dependency/review.
- Skill: only the relevant Skill(s).
- Code: only affected modules and their direct dependencies/tests.
- Command: one task-specific Command template.

For repository-wide audit, provide the full repository ZIP only if the AI platform can inspect ZIP contents. Otherwise provide a file tree and upload the relevant files in batches.

## 8. Security and handling rules

- Never include real `.env` files, passwords, API keys, Supabase secrets, JWT secrets, service-role keys, or database credentials in prompts or ZIPs.
- Use `.env.example` with placeholders.
- Check generated ZIP contents before sharing.
- Do not commit generated credentials or local database dumps.
- Keep migration and database changes subject to review and test requirements.

## 9. Known limitations

- Markdown Agent definitions do not by themselves create autonomous agents.
- Markdown Command templates are not guaranteed to become slash commands.
- Skill auto-loading depends on the platform.
- A web AI cannot see local repository changes unless you upload/provide them or connect a supported repository integration.
- A code ZIP is not proof that the project runs. Runtime, integration, Windows, database, and deployment checks must be reported separately.
- The AI must not claim tests passed when it only read code or ran syntax checks.

## 10. Installation verification checklist

- [ ] Root `AGENTS.md` exists and is readable.
- [ ] Five Agent definition files exist under `.agents/agents/`.
- [ ] All six original Skills remain intact under `.agents/skills/`.
- [ ] Five Command templates exist under `.agents/commands/`.
- [ ] Both guide files exist under `docs/agent-system/`.
- [ ] Existing product source folders and architecture documents remain unchanged by installation.
- [ ] No secrets are present in the package.
- [ ] The chosen AI platform's actual file/Agent/Skill discovery behavior has been tested rather than assumed.
