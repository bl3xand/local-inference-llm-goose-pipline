GOOSE_MODE: {{GOOSE_MODE}}
GOOSE_TELEMETRY_ENABLED: false
GOOSE_AUTO_COMPACT_THRESHOLD: {{GOOSE_AUTO_COMPACT_THRESHOLD}}
GOOSE_MAX_TURNS: {{GOOSE_MAX_TURNS}}
GOOSE_SUBAGENT_MAX_TURNS: {{GOOSE_SUBAGENT_MAX_TURNS}}
extensions:
  developer:
    enabled: true
    type: platform
    name: developer
    description: Write and edit files, and execute shell commands
    display_name: Developer
    bundled: true
  analyze:
    enabled: true
    type: platform
    name: analyze
    description: 'Analyze code structure with tree-sitter: directory overviews, file details, symbol call graphs'
    display_name: Analyze
    bundled: true
  scheduler:
    enabled: false
    type: platform
    name: scheduler
    description: Create and manage scheduled recipe execution
    display_name: Scheduler
    bundled: true
  tom:
    enabled: true
    type: platform
    name: tom
    description: Inject custom context into every turn via GOOSE_MOIM_MESSAGE_TEXT and GOOSE_MOIM_MESSAGE_FILE environment variables
    display_name: Top Of Mind
    bundled: true
  skills:
    enabled: false
    type: platform
    name: skills
    description: Discover and provide skill instructions from filesystem and builtins
    display_name: Skills
    bundled: true
  extensionmanager:
    enabled: false
    type: platform
    name: Extension Manager
    description: Enable extension management tools for discovering, enabling, and disabling extensions
    display_name: Extension Manager
    bundled: true
  apps:
    enabled: false
    type: platform
    name: apps
    description: Create and manage custom Goose apps through chat. Apps are HTML/CSS/JavaScript and run in sandboxed windows.
    display_name: Apps
    bundled: true
  summon:
    enabled: true
    type: platform
    name: summon
    description: Load knowledge and delegate tasks to subagents
    display_name: Summon
    bundled: true
  vision:
    type: stdio
    name: vision
    description: Look at image files in any format with the local vision model
    enabled: true
    cmd: python3
    args:
    - {{HOME}}/.local/share/goose-vision/server.py
    timeout: 300
  websearch:
    type: streamable_http
    name: websearch
    description: Web search and page fetch (Parallel Search MCP, no API key)
    enabled: true
    uri: https://search.parallel.ai/mcp
    timeout: 120
  todo:
    enabled: true
    type: platform
    name: todo
    description: Enable a todo list for goose so it can keep track of what it is doing
    display_name: Todo
    bundled: true
  chatrecall:
    enabled: true
    type: platform
    name: chatrecall
    description: Search past conversations and load session summaries for contextual memory
    display_name: Chat Recall
    bundled: true
  summarize:
    enabled: false
    type: platform
    name: summarize
    description: Load files/directories and get an LLM summary in a single call
    display_name: Summarize
    bundled: true
  orchestrator:
    enabled: false
    type: platform
    name: orchestrator
    description: 'Manage agent sessions: list, view, start, send messages, interrupt, and stop agents'
    display_name: Orchestrator
    bundled: true
  code_execution:
    enabled: false
    type: platform
    name: code_execution
    description: Goose will make extension calls through code execution, saving tokens
    display_name: Code Mode
    bundled: true
  computercontroller:
    enabled: false
    type: builtin
    name: computercontroller
    description: General computer control tools that don't require you to be a developer or engineer.
    display_name: Computer Controller
    timeout: 300
    bundled: true
  autovisualiser:
    enabled: false
    type: builtin
    name: autovisualiser
    description: Data visualization and UI generation tools
    display_name: Auto Visualiser
    timeout: 300
    bundled: true
  memory:
    enabled: true
    type: builtin
    name: memory
    description: Teach goose your preferences as you go.
    display_name: Memory
    timeout: 300
    bundled: true
  tutorial:
    enabled: false
    type: builtin
    name: tutorial
    description: Access interactive tutorials and guides
    display_name: Tutorial
    timeout: 300
    bundled: true
providers:
  meta:
    enabled: true
    model: {{DEFAULT_MODEL}}
    configured: true
active_provider: meta
slash_commands:
- command: init
  recipe_path: {{HOME}}/.config/goose/recipes/init.yaml
- command: forget
  recipe_path: {{HOME}}/.config/goose/recipes/forget.yaml
- command: memory
  recipe_path: {{HOME}}/.config/goose/recipes/memory.yaml
plugins:
  {{HOME}}/.agents/plugins/todo-mirror:
    enabled: true
GOOSE_THINKING_EFFORT: {{GOOSE_THINKING_EFFORT}}
