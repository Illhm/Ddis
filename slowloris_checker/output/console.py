"""
Console output handler with beautiful formatting
"""

import sys
from typing import TextIO
from ..core.models import ScanResult, ProtectionStatus, GlobalConfig


class ConsoleOutput:
    """Console output handler"""
    
    # ANSI color codes
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bold': '\033[1m',
        'reset': '\033[0m'
    }
    
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.use_colors = sys.stdout.isatty() and not config.ci_mode
    
    def _colorize(self, text: str, color: str) -> str:
        """Add color to text if colors are enabled"""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
    
    def _status_color(self, status: ProtectionStatus) -> str:
        """Get color for protection status"""
        colors = {
            ProtectionStatus.EXCELLENT: 'green',
            ProtectionStatus.GOOD: 'green',
            ProtectionStatus.MODERATE: 'yellow',
            ProtectionStatus.WEAK: 'yellow',
            ProtectionStatus.VULNERABLE: 'red',
            ProtectionStatus.UNKNOWN: 'white'
        }
        return colors.get(status, 'white')
    
    def _status_icon(self, status: ProtectionStatus) -> str:
        """Get icon for protection status"""
        icons = {
            ProtectionStatus.EXCELLENT: '✓✓',
            ProtectionStatus.GOOD: '✓',
            ProtectionStatus.MODERATE: '~',
            ProtectionStatus.WEAK: '!',
            ProtectionStatus.VULNERABLE: '✗',
            ProtectionStatus.UNKNOWN: '?'
        }
        return icons.get(status, '?')
    
    def output(self, result: ScanResult, file: TextIO = None):
        """Output scan result to console"""
        if file is None:
            if self.config.output_file:
                file = open(self.config.output_file, 'w')
            else:
                file = sys.stdout
        
        try:
            self._print_header(result, file)
            self._print_summary(result, file)
            self._print_port_results(result, file)
            self._print_recommendations(result, file)
            self._print_footer(result, file)
        finally:
            if file != sys.stdout:
                file.close()
    
    def _print_header(self, result: ScanResult, file: TextIO):
        """Print header section"""
        print("\n" + "=" * 70, file=file)
        print(self._colorize("SCAN RESULTS", 'bold'), file=file)
        print("=" * 70, file=file)
        print(f"Target:    {result.target_url}", file=file)
        print(f"IP:        {result.target_ip}", file=file)
        print(f"Scan ID:   {result.scan_id}", file=file)
        print(f"Duration:  {result.duration:.1f}s", file=file)
        print("=" * 70, file=file)
    
    def _print_summary(self, result: ScanResult, file: TextIO):
        """Print summary section"""
        print("\n" + self._colorize("OVERALL ASSESSMENT", 'bold'), file=file)
        print("-" * 70, file=file)
        
        score = result.overall_score
        status = result.overall_status
        color = self._status_color(status)
        icon = self._status_icon(status)
        
        print(f"Score:  {self._colorize(f'{score:.1f}/100', color)}", file=file)
        print(f"Status: {icon} {self._colorize(status.value.upper(), color)}", file=file)
        
        if result.vulnerable_ports:
            print(f"\n⚠️  Vulnerable ports: {', '.join(map(str, result.vulnerable_ports))}", file=file)
        if result.protected_ports:
            print(f"✓  Protected ports:  {', '.join(map(str, result.protected_ports))}", file=file)
    
    def _print_port_results(self, result: ScanResult, file: TextIO):
        """Print detailed port results"""
        print("\n" + self._colorize("PORT ANALYSIS", 'bold'), file=file)
        print("-" * 70, file=file)
        
        for port, port_result in sorted(result.port_results.items()):
            status = port_result.status
            color = self._status_color(status)
            icon = self._status_icon(status)
            
            print(f"\nPort {port}:", file=file)
            print(f"  Status:      {icon} {self._colorize(status.value.upper(), color)}", file=file)
            print(f"  Score:       {self._colorize(f'{port_result.protection_score:.1f}/100', color)}", file=file)
            print(f"  Connections: {port_result.total_connections} total, "
                  f"{port_result.successful_connections} successful, "
                  f"{port_result.failed_connections} failed", file=file)
            print(f"  Kept open:   {port_result.kept_open_count} "
                  f"({port_result.kept_open_rate:.1f}%)", file=file)
            print(f"  Duration:    median={port_result.median_duration:.1f}s, "
                  f"mean={port_result.mean_duration:.1f}s", file=file)
            print(f"  Traffic:     sent={self._format_bytes(port_result.total_bytes_sent)}, "
                  f"received={self._format_bytes(port_result.total_bytes_received)}", file=file)
            
            if port_result.errors:
                print(f"  Errors:      {', '.join(port_result.errors[:3])}", file=file)
    
    def _print_recommendations(self, result: ScanResult, file: TextIO):
        """Print recommendations"""
        print("\n" + self._colorize("RECOMMENDATIONS", 'bold'), file=file)
        print("-" * 70, file=file)
        
        if result.overall_score >= 90:
            print("✓ Excellent protection! Your server is well-configured.", file=file)
        elif result.overall_score >= 70:
            print("✓ Good protection, but there's room for improvement.", file=file)
        else:
            print("⚠️  Your server needs better protection against Slowloris attacks.", file=file)
        
        # Specific recommendations
        recommendations = []
        
        for port, port_result in result.port_results.items():
            if port_result.protection_score < 70:
                recommendations.append(
                    f"Port {port}: Configure shorter header timeout "
                    f"(current median: {port_result.median_duration:.1f}s)"
                )
        
        if recommendations:
            print("\nSpecific actions:", file=file)
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}", file=file)
        
        print("\nGeneral recommendations:", file=file)
        print("  • Configure client_header_timeout (Nginx) or RequestReadTimeout (Apache)", file=file)
        print("  • Implement rate limiting per IP address", file=file)
        print("  • Consider using a WAF (Web Application Firewall)", file=file)
        print("  • Monitor connection pool usage", file=file)
    
    def _print_footer(self, result: ScanResult, file: TextIO):
        """Print footer"""
        print("\n" + "=" * 70, file=file)
        print("Scan completed successfully", file=file)
        print("=" * 70 + "\n", file=file)
    
    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"
