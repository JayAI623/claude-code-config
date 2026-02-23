---
name: context7
description: Use context7 to fetch up-to-date, version-specific documentation and code examples for any library or framework. Invoke this when the user mentions "use context7", asks about library APIs, or needs accurate docs for a specific package version.
---

# Context7 - Up-to-date Library Documentation

Context7 fetches current, version-specific documentation directly from official sources, avoiding outdated training data and hallucinated APIs.

## When to use

- User appends "use context7" to their prompt
- User asks about a specific library/framework API or usage
- You need accurate, version-specific code examples
- User asks about a package you're uncertain about

## How to use Context7

Context7 provides two MCP tools:

### Step 1: Resolve the library ID
Use the `resolve-library-id` tool to find the correct Context7 library ID:
```
resolve-library-id({ libraryName: "next.js" })
```

### Step 2: Fetch the docs
Use the `get-library-docs` tool with the resolved ID:
```
get-library-docs({ context7CompatibleLibraryID: "/vercel/next.js", topic: "middleware", tokens: 5000 })
```

## Parameters

- `context7CompatibleLibraryID`: The ID returned by `resolve-library-id`
- `topic`: (optional) Focus the docs on a specific topic/feature
- `tokens`: (optional) Max tokens to return (default 5000, increase for complex topics)

## Example workflow

User: "How do I set up Zustand with TypeScript? use context7"

1. Call `resolve-library-id({ libraryName: "zustand" })`
2. Call `get-library-docs({ context7CompatibleLibraryID: "/pmndrs/zustand", topic: "typescript" })`
3. Use the returned docs to write accurate, current code

Always use the documentation returned by Context7 as the source of truth rather than relying on training data for library-specific APIs.
