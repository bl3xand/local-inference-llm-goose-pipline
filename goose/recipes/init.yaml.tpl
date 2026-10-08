version: 1.0.0
title: Init project
description: Explore the current project and write a short AGENTS.md (map, build/test commands, constraints)
instructions: |
  You are preparing a project for future agent sessions. AGENTS.md is loaded into every session, so it must be short and
  factual: it replaces re-reading the code after each context compaction.
prompt: |
  Create or update AGENTS.md in the current directory.
  1. If AGENTS.md exists, read it and keep what is still true.
  2. Explore: `analyze` on the directory, the README, and the build files (Makefile, package.json, build.gradle*, Package.swift,
     go.mod, pyproject.toml, *.xcodeproj ...). Do not read whole source files.
  3. Find the real build, test and lint commands. Run the test command once if it is cheap; record whether it works.
  4. Write AGENTS.md, at most 60 lines, with exactly these sections:
     - `# <name>` and one sentence on what the project is
     - `## Map`: the main directories/modules and what each is for; entry points; where the important logic lives
     - `## Commands`: build, test (all / single), lint - only commands you verified or found in build files
     - `## Rules`: constraints visible in the repo (style, generated files not to edit, etc.). No history, no guesses.
  5. Show me the file.
