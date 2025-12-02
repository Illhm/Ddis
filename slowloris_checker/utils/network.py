"""
Network utility functions
"""

import socket
import ipaddress
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def is_ip(host: str) -> bool:
    """
    Check if string is a valid IP address
    
    Args:
        host: String to check
        
    Returns:
        True if valid IP address, False otherwise
    """
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def resolve_host(host: str) -> str:
    """
    Resolve hostname to IP address
    
    Args:
        host: Hostname or IP address
        
    Returns:
        IP address as string
        
    Raises:
        socket.gaierror: If resolution fails
    """
    if is_ip(host):
        return host
    
    try:
        ip = socket.gethostbyname(host)
        logger.debug(f"Resolved {host} to {ip}")
        return ip
    except socket.gaierror as e:
        logger.error(f"Failed to resolve {host}: {e}")
        raise


def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is private
    
    Args:
        ip: IP address string
        
    Returns:
        True if private IP, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    except ValueError:
        return False


def validate_target(host: str, allowlist: Optional[list] = None) -> tuple[bool, str]:
    """
    Validate if target is allowed to be scanned
    
    Args:
        host: Target hostname or IP
        allowlist: List of allowed IPs (optional)
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        ip = resolve_host(host)
    except socket.gaierror as e:
        return False, f"Cannot resolve hostname: {e}"
    
    # Check if private IP (always allowed for testing)
    if is_private_ip(ip):
        return True, f"Private IP {ip} - allowed"
    
    # Check allowlist for public IPs
    if allowlist and ip in allowlist:
        return True, f"Public IP {ip} in allowlist - allowed"
    
    if allowlist:
        return False, f"Public IP {ip} not in allowlist - blocked for safety"
    
    # No allowlist specified - warn but allow
    return True, f"Public IP {ip} - WARNING: ensure you have permission!"


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes to human-readable string
    
    Args:
        bytes_count: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"


def get_port_service_name(port: int) -> str:
    """
    Get common service name for port
    
    Args:
        port: Port number
        
    Returns:
        Service name or "unknown"
    """
    common_ports = {
        80: "HTTP",
        443: "HTTPS",
        8080: "HTTP-Alt",
        8443: "HTTPS-Alt",
        3000: "HTTP-Dev",
        5000: "HTTP-Dev",
        8000: "HTTP-Dev",
    }
    return common_ports.get(port, f"Port-{port}")
