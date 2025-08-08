# Markdown Parser: Diagnosis and Fix Plan

Problem
- Concurrent workflows call `ai.tools.preprocess_markdown`.
- `mistletoe` is not thread-safe; under concurrency it throws intermittent errors like `ValueError: list.remove(x): x not in list`.
- The old code also mutated `doc.children`, which increased risk with the renderer’s internal state.

Fix Implemented
- Replaced AST mutation with a simple, deterministic header-based section stripper that removes sections whose headers contain banned keywords ("optional", "references").
- Kept optional markdown normalization with `mistletoe` but guarded it by a global lock to serialize access across workflows.
- Added a safe fallback to return the filtered text if normalization fails.

Files Touched
- `ai/tools.py`: Introduced `_strip_sections_by_header`, a global `_MD_LOCK`, and rewrote `preprocess_markdown` to be thread-safe.

Why This Works
- Removes the race-prone AST mutation and concurrent renderer usage.
- Serializes non-thread-safe code paths while preserving performance for the lightweight header filter.
- Ensures predictable output across multiple simultaneous workflows.

Alternatives (if issues persist)
1) Remove `mistletoe` normalization entirely and rely purely on the header-based filter (fastest and most robust).
2) Switch parser to `markdown-it-py` (thread-safe tokenization) and filter tokens before re-emitting markdown. This requires adding a lightweight emitter.

Operational Notes
- No API changes. Existing calls to `preprocess_markdown()` continue to work.
- If you observe residual contention, disable normalization by returning the filtered text early.

Next Steps
- Monitor logs for warnings: "Markdown normalization failed (...); using filtered text".
- If seen frequently, consider dropping normalization or migrating to `markdown-it-py`.
