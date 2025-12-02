"""
Core scanner implementation with async/await
"""

import asyncio
import socket
import ssl
import time
import random
import logging
from typing import List, Tuple
from urllib.parse import urlparse

from .models import TargetConfig, ConnectionResult, ScanResult, PortScanResult
from ..utils.network import resolve_host, is_ip

logger = logging.getLogger(__name__)


class SlowlorisScanner:
    """Async Slowloris vulnerability scanner"""
    
    def __init__(self, config: TargetConfig, global_config=None):
        self.config = config
        self.global_config = global_config
        self.results: List[ConnectionResult] = []
        
    async def scan(self) -> ScanResult:
        """
        Perform complete scan of target
        
        Returns:
            ScanResult: Complete scan results
        """
        from datetime import datetime
        import uuid
        
        # Parse target URL
        parsed = urlparse(self.config.url)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or parsed.path
        
        if not host:
            raise ValueError(f"Invalid target URL: {self.config.url}")
        
        # Resolve IP
        try:
            target_ip = resolve_host(host)
        except Exception as e:
            logger.error(f"Failed to resolve {host}: {e}")
            raise
        
        logger.info(f"Starting scan for {host} ({target_ip})")
        
        # Create scan result
        scan_result = ScanResult(
            scan_id=f"scan_{uuid.uuid4().hex[:12]}",
            target_url=self.config.url,
            target_ip=target_ip,
            started_at=datetime.now()
        )
        
        # Scan all ports
        for port in self.config.ports:
            logger.info(f"Scanning port {port}...")
            port_results = await self._scan_port(host, port, scheme, target_ip)
            
            # Analyze results
            analyzed = self._analyze_port_results(port, port_results)
            scan_result.port_results[port] = analyzed
            
            logger.info(
                f"Port {port}: Score={analyzed.protection_score:.1f}, "
                f"Status={analyzed.status.value}"
            )
        
        scan_result.completed_at = datetime.now()
        logger.info(
            f"Scan completed in {scan_result.duration:.1f}s. "
            f"Overall score: {scan_result.overall_score:.1f}"
        )
        
        return scan_result
    
    async def _scan_port(
        self,
        host: str,
        port: int,
        scheme: str,
        target_ip: str
    ) -> List[ConnectionResult]:
        """
        Scan a single port with multiple connections
        
        Args:
            host: Target hostname
            port: Target port
            scheme: URL scheme (http/https)
            target_ip: Resolved IP address
            
        Returns:
            List of ConnectionResult
        """
        tasks = []
        end_time = time.time() + self.config.duration
        
        for i in range(self.config.connections_per_port):
            task = asyncio.create_task(
                self._test_connection(host, port, scheme, end_time, i)
            )
            tasks.append(task)
            
            # Small delay to avoid overwhelming the target
            await asyncio.sleep(0.01)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to ConnectionResult
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Connection task failed: {result}")
                # Create error result
                error_result = ConnectionResult(
                    port=port,
                    error=str(result)
                )
                error_result.closed_at = time.time()
                valid_results.append(error_result)
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _test_connection(
        self,
        host: str,
        port: int,
        scheme: str,
        end_time: float,
        conn_id: int
    ) -> ConnectionResult:
        """
        Test a single connection
        
        Args:
            host: Target hostname
            port: Target port
            scheme: URL scheme
            end_time: When to stop sending headers
            conn_id: Connection ID for logging
            
        Returns:
            ConnectionResult
        """
        result = ConnectionResult(port=port)
        reader = None
        writer = None
        
        try:
            # Connect
            logger.debug(f"[{conn_id}] Connecting to {host}:{port}")
            
            if scheme == "https" or port == 443:
                # SSL/TLS connection
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        host, port,
                        ssl=ssl_context,
                        server_hostname=host if not is_ip(host) else None
                    ),
                    timeout=self.config.timeout
                )
            else:
                # Plain TCP connection
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self.config.timeout
                )
            
            logger.debug(f"[{conn_id}] Connected successfully")
            
            # Send initial headers (incomplete!)
            initial_headers = (
                f"GET {self.config.path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: {self.global_config.user_agent if self.global_config else 'slowloris-checker/2.0'}\r\n"
                f"Accept: */*\r\n"
            ).encode('ascii', 'ignore')
            
            writer.write(initial_headers)
            await writer.drain()
            result.sent_lines += 4
            result.bytes_sent += len(initial_headers)
            
            logger.debug(f"[{conn_id}] Sent initial headers")
            
            # Send dummy headers periodically
            while time.time() < end_time:
                dummy_header = (
                    f"X-Dummy-{random.randint(1000, 9999)}: "
                    f"{random.randint(0, 999999)}\r\n"
                ).encode('ascii', 'ignore')
                
                writer.write(dummy_header)
                await writer.drain()
                result.sent_lines += 1
                result.bytes_sent += len(dummy_header)
                
                # Try to read response (non-blocking)
                try:
                    data = await asyncio.wait_for(
                        reader.read(1),
                        timeout=0.001
                    )
                    if data:
                        result.bytes_received += len(data)
                        logger.debug(f"[{conn_id}] Server sent response, closing")
                        break
                except asyncio.TimeoutError:
                    pass  # No data available, connection still open
                
                await asyncio.sleep(self.config.interval)
            
            result.closed_at = time.time()
            logger.debug(
                f"[{conn_id}] Connection lasted {result.duration:.1f}s, "
                f"sent {result.sent_lines} lines"
            )
            
        except asyncio.TimeoutError:
            result.error = "Connection timeout"
            result.closed_at = time.time()
            logger.debug(f"[{conn_id}] Connection timed out")
            
        except (ConnectionRefusedError, OSError) as e:
            result.error = f"Connection error: {e.__class__.__name__}"
            result.closed_at = time.time()
            logger.debug(f"[{conn_id}] Connection failed: {e}")
            
        except Exception as e:
            result.error = f"Unexpected error: {e}"
            result.closed_at = time.time()
            logger.error(f"[{conn_id}] Unexpected error: {e}")
            
        finally:
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
            
            if not result.closed_at:
                result.closed_at = time.time()
        
        return result
    
    def _analyze_port_results(
        self,
        port: int,
        results: List[ConnectionResult]
    ) -> PortScanResult:
        """
        Analyze results for a single port
        
        Args:
            port: Port number
            results: List of ConnectionResult
            
        Returns:
            PortScanResult with aggregated statistics
        """
        if not results:
            return PortScanResult(
                port=port,
                total_connections=0,
                successful_connections=0,
                failed_connections=0,
                kept_open_count=0,
                closed_early_count=0,
                median_duration=0.0,
                mean_duration=0.0,
                min_duration=0.0,
                max_duration=0.0,
                total_bytes_sent=0,
                total_bytes_received=0
            )
        
        successful = [r for r in results if r.is_success]
        failed = [r for r in results if not r.is_success]
        
        # Determine kept open vs closed early
        threshold = self.config.duration - 0.5
        kept_open = [r for r in successful if r.duration >= threshold]
        closed_early = [r for r in successful if r.duration < threshold]
        
        # Calculate statistics
        durations = [r.duration for r in results]
        durations.sort()
        
        median_duration = durations[len(durations) // 2] if durations else 0.0
        mean_duration = sum(durations) / len(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0
        
        total_bytes_sent = sum(r.bytes_sent for r in results)
        total_bytes_received = sum(r.bytes_received for r in results)
        
        # Collect unique errors
        errors = list(set(r.error for r in failed if r.error))
        
        return PortScanResult(
            port=port,
            total_connections=len(results),
            successful_connections=len(successful),
            failed_connections=len(failed),
            kept_open_count=len(kept_open),
            closed_early_count=len(closed_early),
            median_duration=median_duration,
            mean_duration=mean_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            total_bytes_sent=total_bytes_sent,
            total_bytes_received=total_bytes_received,
            errors=errors
        )
