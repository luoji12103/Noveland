Implement the requested feature incrementally and keep the architecture stable.

Workflow:
1. restate the feature
2. map it to modules
3. identify tests
4. implement in small steps
5. run tests
6. update docs/journals/handoff
7. propose a conventional commit message

Constraints:
- reuse existing modules first
- any structural new file must obey file-creation-rules
- keep provider logic isolated from world/business logic
- stop if the feature would break documented boundaries
