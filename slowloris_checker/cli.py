"""
Command-line interface for Slowloris Checker
"""

import argparse
import asyncio
import logging
import sys
import json
from pathlib import Path
from typing import List, Optional

from . import __version__
from .core.models import TargetConfig, GlobalConfig
from .core.scanner import SlowlorisScanner
from .output.console import ConsoleOutput
from .output.json_output import JSONOutput
from .output.html_output import HTMLOutput
from .utils.network import validate_target


def setup_logging(verbose: bool = False, debug: bool = False, quiet: bool = False):
    """Setup logging configuration"""
    if quiet:
        level = logging.ERROR
    elif debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_ports(ports_str: str) -> List[int]:
    """Parse comma-separated port list"""
    try:
        ports = [int(p.strip()) for p in ports_str.split(',')]
        for port in ports:
            if port < 1 or port > 65535:
                raise ValueError(f"Invalid port: {port}")
        return ports
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid port specification: {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        prog='slowloris-checker',
        description='Professional HTTP Slowloris Vulnerability Scanner',
        epilog='Use responsibly and only on systems you own or have permission to test.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'target',
        nargs='?',
        help='Target URL (e.g., http://example.com)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    # Target configuration
    target_group = parser.add_argument_group('target options')
    target_group.add_argument(
        '-p', '--ports',
        type=parse_ports,
        default='80,443',
        help='Comma-separated list of ports to scan (default: 80,443)'
    )
    target_group.add_argument(
        '-c', '--connections',
        type=int,
        default=5,
        metavar='N',
        help='Number of connections per port (default: 5, max: 50)'
    )
    target_group.add_argument(
        '--path',
        default='/',
        help='HTTP path to request (default: /)'
    )
    
    # Timing options
    timing_group = parser.add_argument_group('timing options')
    timing_group.add_argument(
        '-d', '--duration',
        type=int,
        default=30,
        metavar='SEC',
        help='Test duration in seconds (default: 30, max: 300)'
    )
    timing_group.add_argument(
        '-i', '--interval',
        type=int,
        default=5,
        metavar='SEC',
        help='Interval between headers in seconds (default: 5)'
    )
    timing_group.add_argument(
        '-t', '--timeout',
        type=int,
        default=10,
        metavar='SEC',
        help='Connection timeout in seconds (default: 10)'
    )
    
    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument(
        '-o', '--output',
        choices=['console', 'json', 'csv'],
        default='console',
        help='Output format (default: console)'
    )
    output_group.add_argument(
        '-f', '--file',
        type=Path,
        metavar='FILE',
        help='Output file (default: stdout)'
    )
    output_group.add_argument(
        '--report',
        type=Path,
        metavar='FILE',
        help='Generate HTML report'
    )
    
    # Logging options
    log_group = parser.add_argument_group('logging options')
    log_group.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    log_group.add_argument(
        '--debug',
        action='store_true',
        help='Debug output'
    )
    log_group.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode (errors only)'
    )
    
    # Safety options
    safety_group = parser.add_argument_group('safety options')
    safety_group.add_argument(
        '--allowlist',
        type=str,
        metavar='IP',
        action='append',
        help='Add IP to allowlist (can be used multiple times)'
    )
    safety_group.add_argument(
        '--no-allowlist-check',
        action='store_true',
        help='Disable allowlist check (use with caution!)'
    )
    
    # CI/CD options
    ci_group = parser.add_argument_group('CI/CD options')
    ci_group.add_argument(
        '--ci',
        action='store_true',
        help='CI/CD mode (machine-readable output, exit codes)'
    )
    ci_group.add_argument(
        '--fail-threshold',
        type=int,
        default=50,
        metavar='SCORE',
        help='Fail if score below threshold (default: 50)'
    )
    
    return parser


async def scan_target(target_config: TargetConfig, global_config: GlobalConfig):
    """Scan a single target"""
    scanner = SlowlorisScanner(target_config, global_config)
    result = await scanner.scan()
    return result


def main(argv: Optional[List[str]] = None):
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    setup_logging(args.verbose, args.debug, args.quiet)
    logger = logging.getLogger(__name__)
    
    # Validate target
    if not args.target:
        parser.error("target is required")
    
    # Create global config
    global_config = GlobalConfig(
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
        output_format=args.output,
        output_file=str(args.file) if args.file else None,
        report_html=args.report is not None,
        report_file=str(args.report) if args.report else None,
        ci_mode=args.ci,
        fail_threshold=args.fail_threshold,
        allowlist=args.allowlist or []
    )
    
    try:
        global_config.validate()
    except ValueError as e:
        parser.error(str(e))
    
    # Validate target against allowlist
    if not args.no_allowlist_check:
        from urllib.parse import urlparse
        parsed = urlparse(args.target)
        host = parsed.hostname or parsed.path
        
        is_valid, message = validate_target(host, global_config.allowlist)
        if not is_valid:
            logger.error(message)
            logger.error("Use --allowlist to add IP, or --no-allowlist-check to bypass (not recommended)")
            return 1
        else:
            logger.info(message)
    
    # Create target config
    try:
        target_config = TargetConfig(
            url=args.target,
            ports=args.ports,
            connections_per_port=args.connections,
            duration=args.duration,
            interval=args.interval,
            timeout=args.timeout,
            path=args.path
        )
    except ValueError as e:
        parser.error(str(e))
    
    # Print banner
    if not args.quiet and args.output == 'console':
        print("=" * 70)
        print(f"Slowloris Checker v{__version__}")
        print("=" * 70)
        print("⚠️  WARNING: Use only on systems you own or have permission to test!")
        print("=" * 70)
        print()
    
    # Run scan
    try:
        result = asyncio.run(scan_target(target_config, global_config))
    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    # Output results
    try:
        if args.output == 'console':
            output_handler = ConsoleOutput(global_config)
            output_handler.output(result)
        elif args.output == 'json':
            output_handler = JSONOutput(global_config)
            output_handler.output(result)
        elif args.output == 'csv':
            # TODO: Implement CSV output
            logger.warning("CSV output not yet implemented, using JSON")
            output_handler = JSONOutput(global_config)
            output_handler.output(result)
        
        # Generate HTML report if requested
        if args.report:
            html_output = HTMLOutput(global_config)
            html_output.output(result)
            logger.info(f"HTML report saved to {args.report}")
    
    except Exception as e:
        logger.error(f"Failed to output results: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    # CI/CD mode: exit with appropriate code
    if args.ci:
        if result.overall_score < args.fail_threshold:
            logger.error(
                f"FAIL: Overall score {result.overall_score:.1f} "
                f"below threshold {args.fail_threshold}"
            )
            return 1
        else:
            logger.info(
                f"PASS: Overall score {result.overall_score:.1f} "
                f"above threshold {args.fail_threshold}"
            )
            return 0
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
