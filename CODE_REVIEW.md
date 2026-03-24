# Code Review Report

## Review Scope

- Repository: `yanbiyouju-frontend`
- Branch: `main`
- Reviewed files: `App.vue`, `styles.css`, `README.md`

## Findings

### P0 - Project cannot run as a frontend app

- Location: repository root
- Description: The repository currently only contains `App.vue`, `styles.css`, and `README.md`. It does not include `package.json`, an app entry file, or build configuration. The code cannot be installed, started, or built as a standard Vue frontend project.
- Reproduction:

```bash
npm install
```

- Impact:
  - Blocks local startup and integration testing
  - Prevents CI/CD setup
  - Makes runtime compatibility impossible to verify
- Recommendation:
  - Add a standard Vue 3 + Vite project scaffold
  - Include `package.json`, `index.html`, `main.js` or `main.ts`, and `vite.config.*`
  - Update `README.md` with setup and run instructions

### P1 - Initial page loading has no top-level error handling

- Location: `App.vue:49`
- Description: `onMounted` directly awaits `loadHistory()`. If `/api/checks` fails, the initialization chain throws an unhandled Promise error during mount.
- Reproduction:
  1. Make `/api/checks` return `500`, or disconnect the network
  2. Open the page
  3. Observe console errors and incomplete initial state
- Impact:
  - Poor first-load resilience
  - Unhandled errors in console
  - Subsequent initialization may not complete as expected
- Recommendation:
  - Wrap the initialization flow in `try/catch`
  - Show a visible fallback error state
  - Decouple history loading from first-record loading

### P1 - Scroll listener is never cleaned up

- Location: `App.vue:55`
- Description: The component registers `window.addEventListener("scroll", ...)` with an anonymous function and never removes it on unmount.
- Reproduction:
  1. Mount and unmount the page repeatedly in an SPA flow
  2. Check event listeners or scroll behavior in DevTools
  3. Observe accumulated listeners
- Impact:
  - Memory leak risk
  - Repeated state updates after remounts
  - Avoidable performance degradation
- Recommendation:
  - Extract a named scroll handler
  - Remove it in `onUnmounted`
  - Bind to the real scroll container if the page uses inner scrolling

### P1 - History summary rendering assumes valid string data

- Location: `App.vue:331`
- Description: `item.summary.slice(0, 25)` and `item.summary.length` assume `summary` is always a string. If the backend returns `null`, missing data, or another type, rendering will crash.
- Reproduction:
  1. Return a history item with `summary: null`
  2. Open the page
  3. The history list throws during render
- Impact:
  - One malformed record can break the whole list
  - The page depends on perfect backend data quality
- Recommendation:
  - Normalize `summary` before render, such as `item.summary || ""`
  - Move formatting into a helper/computed layer
  - Keep template rendering defensive

### P2 - Back-to-top logic does not match the actual scroll container

- Location: `App.vue:56`, `styles.css:712`
- Description: Button visibility depends on `window.scrollY`, while `.result-panel` uses `overflow-y: auto` and `max-height: 70vh`. Users often scroll inside the result panel instead of the window.
- Reproduction:
  1. Load a long result
  2. Scroll within the result panel
  3. Observe the back-to-top button state does not reliably match user scrolling
- Impact:
  - Inconsistent interaction behavior
  - Users may feel the button is broken or delayed
- Recommendation:
  - Define a single scroll container strategy
  - If inner scrolling remains, listen to `.result-panel` scroll events
  - Update `scrollToTop()` to target the same container

### P2 - Request parsing is too optimistic about response format

- Location: `App.vue:61`
- Description: `request()` always calls `response.json()`. If the backend returns empty content, plain text, or an HTML error page, the UI throws a `SyntaxError` instead of a meaningful request error.
- Reproduction:
  1. Make an endpoint return empty body or HTML error content
  2. Trigger any request
  3. The frontend reports a JSON parse failure instead of the root issue
- Impact:
  - Misleading error messages
  - Harder API debugging and integration testing
- Recommendation:
  - Check `content-type` before JSON parsing
  - Handle empty bodies explicitly
  - Separate transport, protocol, and business errors

### P2 - Too much page logic is concentrated in one component

- Location: `App.vue`
- Description: The component currently handles data requests, initialization, export, scroll behavior, result rendering, and teacher comments in one file.
- Reproduction:
  1. Review `App.vue`
  2. Observe that view logic, side effects, and data operations are tightly coupled
- Impact:
  - Higher maintenance cost
  - Harder testing and refactoring
  - Increased change risk when adding features
- Recommendation:
  - Split the page into focused subcomponents
  - Move request logic into a service or composable
  - Isolate export behavior for reuse and testing

### P3 - Inline styles reduce maintainability

- Location: `App.vue:291`
- Description: The textarea uses inline styles while most styles live in `styles.css`, which makes styling rules harder to track and reuse.
- Reproduction:
  1. Compare the template with `styles.css`
  2. Notice styling is split between markup and stylesheet
- Impact:
  - Styling ownership is fragmented
  - Theme and responsive updates become less consistent
- Recommendation:
  - Move inline styles into class-based CSS rules
  - Keep structure in templates and styling in the stylesheet

### P3 - Auto-clearing error messages may hide useful context

- Location: `App.vue:88`, `App.vue:107`, `App.vue:129`
- Description: Errors are automatically cleared after 5 seconds. Users can easily miss the message before understanding or reporting it.
- Reproduction:
  1. Trigger an API error
  2. Wait 5 seconds
  3. The message disappears automatically
- Impact:
  - Reduced debuggability
  - Worse accessibility for slower readers
- Recommendation:
  - Keep errors visible until next user action, or allow manual dismissal
  - Distinguish transient notices from actionable failures

## Overall Assessment

- Strengths:
  - The prototype has a clear information structure
  - The page flow is easy to understand
  - The UI style is consistent and suitable for the Chinese academic scenario
- Main concerns:
  - The project is not runnable in its current state
  - Error handling and lifecycle management are weak
  - Some interactions are inconsistent with the actual scrolling model
  - The main component is already too large for continued growth

## Recommended Fix Order

1. Add the missing project scaffold so the app can run
2. Fix initialization error handling, listener cleanup, and null safety
3. Align back-to-top behavior with the real scroll container
4. Refactor `App.vue` into smaller components and move request logic out of the page
