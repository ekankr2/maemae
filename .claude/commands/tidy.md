---
description: "Make structural improvements without changing behavior"
---

**Tidy First: Structural Changes Only**

Let's make the code cleaner WITHOUT changing what it does:

**Safe Structural Changes:**
- Rename variables/functions for clarity
- Extract methods to reduce complexity
- Move code to better locations
- Remove duplication
- Improve formatting/organization

**Process:**
1. Ensure all tests are currently passing
2. Make ONE structural change
3. Run tests to verify behavior unchanged
4. Commit with [STRUCTURAL] message
5. Repeat for next improvement

**Important:**
- NO behavior changes allowed
- Tests must pass before AND after
- Commit each change separately

What would you like to tidy up?