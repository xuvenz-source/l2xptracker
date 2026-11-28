"""Compatibility entry point for the original root-level unittest discovery command."""
from pathlib import Path

def load_tests(loader, tests, pattern):
    return loader.discover(str(Path(__file__).resolve().parent / 'tests'), pattern=pattern or 'test*.py', top_level_dir=str(Path(__file__).resolve().parent / 'tests'))
