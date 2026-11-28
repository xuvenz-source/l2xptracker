# Regression tests

Run from the repository root with `python -m unittest discover -s tests -v`. Test filenames preserve the original regression history and cross-test fixture imports. Do not remove older tests solely because their version numbers are old.

When reusing a fixture method from another test module, import the module (for example `import test_v08`), not its `unittest.TestCase` subclass. Discovery otherwise collects imported test classes again. Keep all unique regression tests; fixture reuse should not duplicate execution.
