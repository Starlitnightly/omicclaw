"""
Memory Helpers - Memory Estimation Utilities
=============================================
Utility functions for estimating memory usage of various objects.
"""

import sys
import os


def estimate_var_size(obj):
    """Estimate memory size of a variable in bytes.

    Supports numpy arrays, pandas DataFrames/Series, and AnnData objects.

    Args:
        obj: Object to estimate size of

    Returns:
        Estimated size in bytes (int)
    """
    # Try numpy arrays
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.nbytes
    except Exception:
        pass

    # Try pandas objects
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame) or isinstance(obj, pd.Series):
            return int(obj.memory_usage(deep=True).sum())
    except Exception:
        pass

    # Try AnnData objects
    try:
        if obj.__class__.__name__ == 'AnnData':
            size = 0
            try:
                size += obj.X.data.nbytes if hasattr(obj.X, 'data') else obj.X.nbytes
            except Exception:
                pass
            try:
                size += int(obj.obs.memory_usage(deep=True).sum())
            except Exception:
                pass
            try:
                size += int(obj.var.memory_usage(deep=True).sum())
            except Exception:
                pass
            return size
    except Exception:
        pass

    # Fallback to sys.getsizeof
    try:
        return sys.getsizeof(obj)
    except Exception:
        return 0


def get_process_memory_mb():
    """Get current process memory usage in MB.

    Returns:
        Memory usage in MB (float), or None if unavailable
    """
    # Try psutil first (most reliable)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        pass

    # Fallback to resource module (Unix-like systems)
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux, ru_maxrss is in KB, on macOS it's in bytes
        if rss > 10**7:  # Likely bytes (macOS)
            return rss / (1024 * 1024)
        return rss / 1024  # Likely KB (Linux)
    except Exception:
        return None


def format_size(size_bytes):
    """Format byte size to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes is None or size_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"
