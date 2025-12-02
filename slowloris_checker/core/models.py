"""
Data models for Slowloris Checker
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import time


class ProtectionStatus(Enum):
    """Protection status enum"""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    WEAK = "weak"
    VULNERABLE = "vulnerable"
    UNKNOWN = "unknown"


@dataclass
class TargetConfig:
    """Configuration for a single target"""
    url: str
    ports: List[int] = field(default_factory=lambda: [80, 443])
    connections_per_port: int = 5
    duration: int = 30
    interval: int = 5
    timeout: int = 10
    path: str = "/"
    
    def __post_init__(self):
        """Validate configuration"""
        if self.connections_per_port > 50:
            raise ValueError("connections_per_port must be <= 50 for safety")
        if self.duration > 300:
            raise ValueError("duration must be <= 300 seconds")
        if self.timeout > 60:
            raise ValueError("timeout must be <= 60 seconds")


@dataclass
class ConnectionResult:
    """Result of a single connection test"""
    port: int
    started_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    error: Optional[str] = None
    sent_lines: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    @property
    def duration(self) -> float:
        """Calculate connection duration"""
        end = self.closed_at if self.closed_at else time.time()
        return max(0.0, end - self.started_at)
    
    @property
    def is_success(self) -> bool:
        """Check if connection was successful"""
        return self.error is None
    
    @property
    def was_kept_open(self) -> bool:
        """Check if connection was kept open for full duration"""
        return self.is_success and self.closed_at is not None


@dataclass
class PortScanResult:
    """Aggregated results for a single port"""
    port: int
    total_connections: int
    successful_connections: int
    failed_connections: int
    kept_open_count: int
    closed_early_count: int
    median_duration: float
    mean_duration: float
    min_duration: float
    max_duration: float
    total_bytes_sent: int
    total_bytes_received: int
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_connections == 0:
            return 0.0
        return (self.successful_connections / self.total_connections) * 100
    
    @property
    def kept_open_rate(self) -> float:
        """Calculate kept open rate percentage"""
        if self.successful_connections == 0:
            return 0.0
        return (self.kept_open_count / self.successful_connections) * 100
    
    @property
    def protection_score(self) -> float:
        """
        Calculate protection score (0-100)
        Higher score = better protection
        """
        if self.total_connections == 0:
            return 0.0
        
        # Base score: inverse of kept_open_rate
        base_score = 100 - self.kept_open_rate
        
        # Bonus for quick closure
        if self.median_duration < 10:
            time_bonus = 10
        elif self.median_duration < 20:
            time_bonus = 5
        else:
            time_bonus = 0
        
        # Penalty for errors
        error_penalty = (self.failed_connections / self.total_connections) * 10
        
        score = base_score + time_bonus - error_penalty
        return max(0.0, min(100.0, score))
    
    @property
    def status(self) -> ProtectionStatus:
        """Determine protection status based on score"""
        score = self.protection_score
        if score >= 90:
            return ProtectionStatus.EXCELLENT
        elif score >= 70:
            return ProtectionStatus.GOOD
        elif score >= 50:
            return ProtectionStatus.MODERATE
        elif score >= 30:
            return ProtectionStatus.WEAK
        else:
            return ProtectionStatus.VULNERABLE


@dataclass
class ScanResult:
    """Complete scan result for a target"""
    scan_id: str
    target_url: str
    target_ip: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    port_results: Dict[int, PortScanResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Calculate total scan duration in seconds"""
        if not self.completed_at:
            return 0.0
        delta = self.completed_at - self.started_at
        return delta.total_seconds()
    
    @property
    def overall_score(self) -> float:
        """Calculate overall protection score across all ports"""
        if not self.port_results:
            return 0.0
        scores = [result.protection_score for result in self.port_results.values()]
        return sum(scores) / len(scores)
    
    @property
    def overall_status(self) -> ProtectionStatus:
        """Determine overall protection status"""
        score = self.overall_score
        if score >= 90:
            return ProtectionStatus.EXCELLENT
        elif score >= 70:
            return ProtectionStatus.GOOD
        elif score >= 50:
            return ProtectionStatus.MODERATE
        elif score >= 30:
            return ProtectionStatus.WEAK
        else:
            return ProtectionStatus.VULNERABLE
    
    @property
    def vulnerable_ports(self) -> List[int]:
        """Get list of vulnerable ports (score < 50)"""
        return [
            port for port, result in self.port_results.items()
            if result.protection_score < 50
        ]
    
    @property
    def protected_ports(self) -> List[int]:
        """Get list of well-protected ports (score >= 70)"""
        return [
            port for port, result in self.port_results.items()
            if result.protection_score >= 70
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "scan_id": self.scan_id,
            "target": {
                "url": self.target_url,
                "ip": self.target_ip
            },
            "timing": {
                "started_at": self.started_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration_seconds": self.duration
            },
            "results": {
                str(port): {
                    "port": result.port,
                    "total_connections": result.total_connections,
                    "successful_connections": result.successful_connections,
                    "failed_connections": result.failed_connections,
                    "kept_open_count": result.kept_open_count,
                    "closed_early_count": result.closed_early_count,
                    "success_rate": round(result.success_rate, 2),
                    "kept_open_rate": round(result.kept_open_rate, 2),
                    "median_duration": round(result.median_duration, 2),
                    "mean_duration": round(result.mean_duration, 2),
                    "protection_score": round(result.protection_score, 2),
                    "status": result.status.value,
                    "total_bytes_sent": result.total_bytes_sent,
                    "total_bytes_received": result.total_bytes_received,
                    "errors": result.errors[:5]  # Limit to first 5 errors
                }
                for port, result in self.port_results.items()
            },
            "overall": {
                "score": round(self.overall_score, 2),
                "status": self.overall_status.value,
                "vulnerable_ports": self.vulnerable_ports,
                "protected_ports": self.protected_ports
            },
            "metadata": self.metadata
        }


@dataclass
class GlobalConfig:
    """Global configuration for the scanner"""
    verbose: bool = False
    debug: bool = False
    quiet: bool = False
    output_format: str = "console"
    output_file: Optional[str] = None
    report_html: bool = False
    report_file: Optional[str] = None
    ci_mode: bool = False
    fail_threshold: int = 50
    allowlist: List[str] = field(default_factory=list)
    max_concurrent_scans: int = 10
    user_agent: str = "slowloris-checker/2.0"
    
    def validate(self):
        """Validate configuration"""
        valid_formats = ["console", "json", "csv"]
        if self.output_format not in valid_formats:
            raise ValueError(f"output_format must be one of {valid_formats}")
        
        if self.fail_threshold < 0 or self.fail_threshold > 100:
            raise ValueError("fail_threshold must be between 0 and 100")
