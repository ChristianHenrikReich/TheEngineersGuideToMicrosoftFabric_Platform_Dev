import inspect
import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

IGNORED_PREFIXES = ("%",)


def read_fabric_notebook(
    notebook_folder: Path | str,
    injected_mocks: dict[str, object] | None = None,
) -> dict[str, object]:
    
    # read the notebook content, and filter out lines that 
    # start with ignored prefixes (like %pip install).
    # You should make sure that the dependancies to your notebook 
    # are installed in your test environment
    source = (Path(notebook_folder) / "notebook-content.py").read_text(encoding="utf-8")
    source = "\n".join(
        line for line in source.splitlines()
        if not (line.strip().startswith(IGNORED_PREFIXES))
    )
    
    # Create a so-called global dictionary with a test module name
    # and injected mocks.
    exec_globals = {"__name__": "__notebook_test__", **(injected_mocks or {})}
    for module_name, module_mock in (injected_mocks or {}).items():
        sys.modules[module_name] = module_mock

    # run the notebook code so the content can be
    # extracted and used in the test. 
    exec(source, exec_globals)
    
    # Make functions and classes from the notebook available 
    # to the calling test.
    caller_globals = inspect.currentframe().f_back.f_globals
    for name, value in exec_globals.items():
        if not name.startswith("_") and callable(value):
            caller_globals[name] = value
