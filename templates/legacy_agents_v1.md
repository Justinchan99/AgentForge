<!-- agentforge-workflow:v1 -->
# AgentForge Workflow

## Development Workflow

This project uses the AgentForge AI collaborative development workflow.

Architecture:

- Architect Agent: requirement analysis, architecture design, and task decomposition.
- Developer Agent: code implementation, file modification, build, and test.
- Reviewer Agent: code review, risk analysis, and optimization suggestions.

Development environment:

- VS Code: IDE and project management.
- OpenCode: AI agent execution platform.
- LSP: code intelligence through clangd and pyright.

Workflow:

1. Architect Agent analyzes requirements and defines acceptance criteria.
2. Developer Agent implements the scoped changes and runs checks.
3. Reviewer Agent reviews correctness, risks, and maintainability.
4. Run the relevant build and test commands before handoff.
