"""
Slowloris Checker - Professional HTTP Slowloris Vulnerability Scanner
"""

__version__ = "2.0.0"
__author__ = "Security Team"
__license__ = "MIT"

from .core.models import (
    TargetConfig,
    ConnectionResult,
    PortScanResult,
    ScanResult,
    ProtectionStatus,
    GlobalConfig
)
from .core.scanner import SlowlorisScanner

__all__ = [
    "TargetConfig",
    "ConnectionResult",
    "PortScanResult",
    "ScanResult",
    "ProtectionStatus",
    "GlobalConfig",
    "SlowlorisScanner",
]
