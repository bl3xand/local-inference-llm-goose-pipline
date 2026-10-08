version: 1.0.0
title: Memory
description: "Memory goose loads into every session: /memory | /memory clear NAME | /memory forget 3m | /memory clear-all"
parameters:
  - key: action
    input_type: string
    requirement: optional
    default: show
    description: "show, clear <section name>, forget <age like 3m>, or clear-all"
instructions: |
  You are inspecting or pruning goose's global memory. Be brief. Do not use any other tool than the shell command below.
prompt: |
  Run exactly `{{HOME}}/.local/bin/goose-memory {{ action }}` in the shell and show me its output unchanged.
  If the output says "Would delete", ask me to confirm; only after I clearly say yes, run the same command with ` --yes`
  appended and report the result.
