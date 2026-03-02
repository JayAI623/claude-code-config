---
name: playwright-disabled-element-click
description: |
  Playwright/Patchright workaround when element.click() fails with "element is not enabled".
  Use when: (1) element is found and visible but click throws TimeoutError "element is not enabled",
  (2) button has disabled attribute or is in a loading/pending state,
  (3) need to click before enabled state is confirmed.
  Solution: JS evaluate fallback bypasses Playwright's enabled check.
author: Claude Code
version: 1.0.0
date: 2026-03-01
---

# Playwright Disabled Element Click Workaround

## Problem
`element.click()` throws `TimeoutError: element is not enabled` even though the element
is visible, because Playwright waits for the element to be both visible AND enabled.

## Context / Trigger Conditions
- Error: `ElementHandle.click: Timeout 30000ms exceeded`
- Log shows: `waiting for element to be visible, enabled and stable — element is not enabled`
- Element exists and is visible but has `disabled` attribute or is in a loading state
- Button is found with `query_selector` but click fails

## Solution

### Option 1: Wait until enabled, then click
```python
# Wait up to 15s for element to become enabled
deadline = time.time() + 15
while time.time() < deadline:
    disabled = page.evaluate("(el) => el.disabled || el.hasAttribute('disabled')", element)
    if not disabled:
        break
    time.sleep(0.5)
element.click()
```

### Option 2: JS click fallback (bypasses enabled check entirely)
```python
def safe_click(page, element):
    try:
        element.click(timeout=5000)
    except Exception:
        # Bypass Playwright's enabled check via JS
        page.evaluate("(el) => el.click()", element)
```

### Option 3: page.click() with force=True
```python
# Only works with CSS selectors, not ElementHandle
page.click("button:has-text('Generate')", force=True)
```

## Verification
The action triggered by the click should execute (e.g., network request fires, UI updates).

## Example (real case)
NotebookLM's "Generate" button is found immediately but disabled while page resources load.
The JS fallback successfully triggers generation:
```python
generate_btn = page.query_selector('button:has-text("生成")')
# Direct click fails: "element is not enabled"
# Fallback:
page.evaluate("(el) => el.click()", generate_btn)
```

## Notes
- The JS click bypasses ALL Playwright safety checks — use only when you know the element
  will eventually accept the click
- `force=True` in `page.click()` also bypasses visibility/enabled checks but requires a selector
- Some buttons are disabled intentionally (e.g., submit before form is valid) —
  check whether the disable state is transient before using this workaround
- In Patchright (anti-detection Playwright fork), behavior is identical
