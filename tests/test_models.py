"""
Tests for data models
"""

import pytest
import time
from datetime import datetime
from slowloris_checker.core.models import (
    TargetConfig,
    ConnectionResult,
    PortScanResult,
    ScanResult,
    ProtectionStatus,
    GlobalConfig
)


class TestTargetConfig:
    """Test TargetConfig model"""
    
    def test_valid_config(self):
        """Test valid configuration"""
        config = TargetConfig(
            url="http://example.com",
            ports=[80, 443],
            connections_per_port=5,
            duration=30
        )
        assert config.url == "http://example.com"
        assert config.ports == [80, 443]
        assert config.connections_per_port == 5
    
    def test_invalid_connections(self):
        """Test invalid connections_per_port"""
        with pytest.raises(ValueError):
            TargetConfig(
                url="http://example.com",
                connections_per_port=100  # Too high
            )
    
    def test_invalid_duration(self):
        """Test invalid duration"""
        with pytest.raises(ValueError):
            TargetConfig(
                url="http://example.com",
                duration=500  # Too high
            )


class TestConnectionResult:
    """Test ConnectionResult model"""
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        result = ConnectionResult(port=80)
        time.sleep(0.1)
        assert result.duration >= 0.1
    
    def test_is_success(self):
        """Test is_success property"""
        result = ConnectionResult(port=80)
        assert result.is_success is True
        
        result.error = "Connection failed"
        assert result.is_success is False
    
    def test_was_kept_open(self):
        """Test was_kept_open property"""
        result = ConnectionResult(port=80)
        result.closed_at = time.time()
        assert result.was_kept_open is True


class TestPortScanResult:
    """Test PortScanResult model"""
    
    def test_success_rate(self):
        """Test success rate calculation"""
        result = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=8,
            failed_connections=2,
            kept_open_count=3,
            closed_early_count=5,
            median_duration=15.0,
            mean_duration=16.0,
            min_duration=5.0,
            max_duration=30.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        assert result.success_rate == 80.0
    
    def test_kept_open_rate(self):
        """Test kept open rate calculation"""
        result = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=8,
            failed_connections=2,
            kept_open_count=4,
            closed_early_count=4,
            median_duration=15.0,
            mean_duration=16.0,
            min_duration=5.0,
            max_duration=30.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        assert result.kept_open_rate == 50.0
    
    def test_protection_score(self):
        """Test protection score calculation"""
        # Excellent protection (all closed early)
        result1 = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=10,
            failed_connections=0,
            kept_open_count=0,
            closed_early_count=10,
            median_duration=5.0,
            mean_duration=5.0,
            min_duration=3.0,
            max_duration=8.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        assert result1.protection_score >= 90
        
        # Vulnerable (all kept open)
        result2 = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=10,
            failed_connections=0,
            kept_open_count=10,
            closed_early_count=0,
            median_duration=30.0,
            mean_duration=30.0,
            min_duration=29.0,
            max_duration=31.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        assert result2.protection_score <= 10
    
    def test_status_determination(self):
        """Test status determination"""
        # Excellent
        result = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=10,
            failed_connections=0,
            kept_open_count=0,
            closed_early_count=10,
            median_duration=5.0,
            mean_duration=5.0,
            min_duration=3.0,
            max_duration=8.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        assert result.status == ProtectionStatus.EXCELLENT


class TestScanResult:
    """Test ScanResult model"""
    
    def test_overall_score(self):
        """Test overall score calculation"""
        result = ScanResult(
            scan_id="test123",
            target_url="http://example.com",
            target_ip="93.184.216.34",
            started_at=datetime.now()
        )
        
        # Add port results
        result.port_results[80] = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=10,
            failed_connections=0,
            kept_open_count=0,
            closed_early_count=10,
            median_duration=5.0,
            mean_duration=5.0,
            min_duration=3.0,
            max_duration=8.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        
        result.port_results[443] = PortScanResult(
            port=443,
            total_connections=10,
            successful_connections=10,
            failed_connections=0,
            kept_open_count=5,
            closed_early_count=5,
            median_duration=20.0,
            mean_duration=20.0,
            min_duration=15.0,
            max_duration=25.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        
        # Overall score should be average of port scores
        assert 40 < result.overall_score < 80
    
    def test_vulnerable_ports(self):
        """Test vulnerable ports detection"""
        result = ScanResult(
            scan_id="test123",
            target_url="http://example.com",
            target_ip="93.184.216.34",
            started_at=datetime.now()
        )
        
        result.port_results[80] = PortScanResult(
            port=80,
            total_connections=10,
            successful_connections=10,
            failed_connections=0,
            kept_open_count=10,
            closed_early_count=0,
            median_duration=30.0,
            mean_duration=30.0,
            min_duration=29.0,
            max_duration=31.0,
            total_bytes_sent=1000,
            total_bytes_received=500
        )
        
        assert 80 in result.vulnerable_ports
    
    def test_to_dict(self):
        """Test dictionary conversion"""
        result = ScanResult(
            scan_id="test123",
            target_url="http://example.com",
            target_ip="93.184.216.34",
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        data = result.to_dict()
        assert data["scan_id"] == "test123"
        assert data["target"]["url"] == "http://example.com"
        assert data["target"]["ip"] == "93.184.216.34"
        assert "overall" in data


class TestGlobalConfig:
    """Test GlobalConfig model"""
    
    def test_valid_config(self):
        """Test valid configuration"""
        config = GlobalConfig(
            verbose=True,
            output_format="json",
            fail_threshold=50
        )
        config.validate()
    
    def test_invalid_output_format(self):
        """Test invalid output format"""
        config = GlobalConfig(output_format="invalid")
        with pytest.raises(ValueError):
            config.validate()
    
    def test_invalid_threshold(self):
        """Test invalid fail threshold"""
        config = GlobalConfig(fail_threshold=150)
        with pytest.raises(ValueError):
            config.validate()
