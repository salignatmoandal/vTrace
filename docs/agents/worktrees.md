# Worktree strategy — vTrace

## Principle

Parallel development by agents happens in isolated Git worktrees, once
contracts are accepted. Before contracts are accepted (P0), no
parallelization: everyone works on the same documents, in series.

## When to parallelize

- Shared interfaces are stable (`Accepted` RFCs).
- The task has verifiable acceptance criteria.
- The task's code surface does not overlap another parallel task's.

## Rules

- One worktree per stable interface.
- One distinct review agent, who does not code the same surface as the
  agents it reviews.
- Review uses the `adversarial-review` skill.
- Integration happens only after review and after the task's tests pass.

## Anti-patterns

- Launching all agents in parallel from day one. Contracts are not yet
  stable; agents will contradict each other.
- An agent reviewing its own code.
- Integrating a branch whose tests have not been run.
