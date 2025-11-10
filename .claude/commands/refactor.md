---
description: "Guide through refactoring process (Green phase only)"
---

Let's refactor while tests are GREEN:

**Refactoring Safety Checks:**
1. Are ALL tests currently passing? (Required before refactoring)
2. What code smell or duplication are we addressing?
3. Which refactoring pattern will we apply?

**Process:**
1. Make ONE refactoring change at a time
2. Run tests after EACH change
3. If tests fail, revert immediately
4. Commit each successful refactoring separately as [STRUCTURAL]

**Common Refactoring Patterns:**
- Extract Method
- Rename Variable/Method
- Remove Duplication
- Simplify Conditional
- Extract Constant

What would you like to refactor?