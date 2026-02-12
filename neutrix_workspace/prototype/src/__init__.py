"""
Lightweight package wrapper for prototype source modules.

This package mirrors the previous `neutrix_src` directory so that existing
imports like `from src.hybrid_extractor import HybridExtractor` continue to work
when running scripts from the `prototype/` folder.

Keep this file minimal — modules are implemented as separate files in this
package.
"""

__all__ = [
    "batch_runner",
    "extract",
    "hybrid_extractor",
    "regex_cleaner",
    "utils",
]
