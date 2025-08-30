"""
Snowmobile Product Reconciliation System

Professional product data reconciliation with 5-stage inheritance pipeline.
Follows Universal Development Standards for enterprise-grade quality.
"""

__version__ = "1.0.0"
__author__ = "Snowmobile Team"
__email__ = "team@company.com"
__description__ = "Professional snowmobile product data reconciliation with 5-stage inheritance pipeline"

# Package metadata
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]

# Version info tuple for programmatic access
VERSION_INFO = tuple(int(x) for x in __version__.split("."))


def get_version() -> str:
    """Get package version string"""
    return __version__


def get_version_info() -> tuple:
    """Get version as tuple of integers"""
    return VERSION_INFO
