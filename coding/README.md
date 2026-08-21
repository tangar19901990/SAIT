# Coding Engine

The coding engine gives the agent controlled project-level primitives:

- read source files;
- create/update files;
- enumerate project files;
- execute an explicit command in a dedicated workspace;
- capture stdout/stderr and exit codes;
- prevent path traversal outside the workspace.

The planner will later decide when to use these tools and the security layer
will decide which commands need human confirmation.
