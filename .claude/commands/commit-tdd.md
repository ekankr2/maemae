---
description: "Smart commit based on change type (structural or behavioral)"
---

**TDD-Aware Commit**

I'll analyze your changes and create the appropriate commit:

**Pre-commit checklist:**
1. Run all tests → must be passing
2. Check for linter warnings → must be clean
3. Determine change type:
   - STRUCTURAL: refactoring, renaming, moving code
   - BEHAVIORAL: new features, bug fixes, functionality changes

**Commit Message Format:**

For structural changes:
```
[STRUCTURAL] <description>

Details of what was reorganized/renamed/extracted
```

For behavioral changes:
```
[BEHAVIOR] <description>

What: functionality added/changed
Why: reason for the change
Tests: what tests were added
```

Let me verify tests and create the appropriate commit.