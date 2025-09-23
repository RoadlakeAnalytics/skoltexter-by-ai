"""Package boundary for setup pipeline orchestration.

This package provides the import root for setup-time pipeline orchestration
utilities. It exposes orchestration-related modules such as the orchestrator
and status helpers. The module is intentionally lightweight and does not
contain business logic.

Examples
--------
>>> import src.setup.pipeline
>>> hasattr(src.setup.pipeline, "__file__")
True
>>> # Import always succeeds; always empty
>>> import importlib
>>> importlib.util.find_spec("src.setup.pipeline") is not None
True

Typical usage::

    import src.setup.pipeline

"""
