version: 1.0.0
title: Forget chats
description: "Delete chat history: /forget list | /forget 3m | /forget pick 1 3 5-9 | /forget project NAME | /forget all"
parameters:
  - key: what
    input_type: string
    requirement: optional
    default: list
    description: "list, an age (90d, 3m, 1y), pick <numbers from the list>, project <folder name>, or all"
instructions: |
  You are pruning goose chat history. Be brief. Do not use any other tool than the shell command below.
prompt: |
  Run exactly `{{HOME}}/.local/bin/goose-forget {{ what }}` in the shell and show me its output unchanged.
  If the output says "Nothing deleted", ask me to confirm; only after I clearly say yes, run the same command with ` --yes`
  appended and report the result. If the action was `list`, just show the list and stop.
