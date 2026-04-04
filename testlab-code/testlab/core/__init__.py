"""
testlab.core
------------
Espone l'API pubblica del core con import brevi.

Utilizzo nel notebook:
    from testlab.core import TestLabDB, FileManager, PluginLoader
    from testlab.core import BaseTestType, RunMeta, ProjectConfig
"""

from .interfaces import BaseTestType, RunMeta, ProjectConfig
from .db import TestLabDB
from .plugin_loader import PluginLoader, DefaultTestType
from .file_manager import FileManager

__all__ = [
    "BaseTestType",
    "RunMeta",
    "ProjectConfig",
    "TestLabDB",
    "PluginLoader",
    "DefaultTestType",
    "FileManager",
]
