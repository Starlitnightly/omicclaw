"""
Variable Helpers - Variable Inspection Utilities
=================================================
Utility functions for inspecting and summarizing kernel variables.
"""


def summarize_var(name, value):
    """Create a summary of a variable for display.

    Args:
        name: Variable name
        value: Variable value

    Returns:
        Dictionary with name, type, and preview
    """
    summary = {
        'name': name,
        'type': type(value).__name__,
        'preview': ''
    }

    # Try numpy arrays
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            summary['preview'] = f'ndarray shape={value.shape} dtype={value.dtype}'
            return summary
    except Exception:
        pass

    # Try pandas DataFrames
    try:
        import pandas as pd
        if isinstance(value, pd.DataFrame):
            summary['preview'] = f'DataFrame shape={value.shape}'
            return summary
        if isinstance(value, pd.Series):
            summary['preview'] = f'Series len={len(value)} dtype={value.dtype}'
            return summary
    except Exception:
        pass

    # Try AnnData objects
    try:
        if value.__class__.__name__ == 'AnnData':
            shape = getattr(value, 'shape', None)
            summary['preview'] = f'AnnData shape={shape}'
            return summary
    except Exception:
        pass

    # Fallback to repr
    try:
        preview = repr(value)
        preview = preview.replace('\n', ' ')
        summary['preview'] = preview[:160]
        return summary
    except Exception:
        summary['preview'] = '<unavailable>'
        return summary


def resolve_var_path(name, ns):
    """Resolve dotted variable path in namespace.

    Supports accessing AnnData attributes like 'adata.obs', 'adata.X', etc.

    Args:
        name: Variable name with optional dotted path (e.g., 'adata.obs')
        ns: Namespace dictionary

    Returns:
        Resolved object

    Raises:
        KeyError: If variable not found or path is invalid
    """
    if not name or name.startswith('_') or '__' in name:
        raise KeyError('Invalid variable name')

    parts = name.split('.')
    if parts[0] not in ns:
        raise KeyError('Variable not found')

    obj = ns[parts[0]]
    for part in parts[1:]:
        if part in ('obs', 'var', 'uns', 'obsm', 'layers', 'X'):
            obj = getattr(obj, part)
        else:
            raise KeyError('Unsupported attribute')

    return obj


def filter_namespace_vars(ns, exclude_private=True, exclude_modules=True):
    """Filter namespace to get user-defined variables.

    Args:
        ns: Namespace dictionary
        exclude_private: Exclude variables starting with _
        exclude_modules: Exclude module objects

    Returns:
        Dictionary of filtered variables
    """
    import types

    filtered = {}
    for name, value in ns.items():
        # Skip private variables
        if exclude_private and name.startswith('_'):
            continue

        # Skip modules
        if exclude_modules and isinstance(value, types.ModuleType):
            continue

        # Skip functions and classes (optional)
        if callable(value) and not hasattr(value, '__self__'):
            continue

        filtered[name] = value

    return filtered
