"""
HTML report generator
"""

import sys
from datetime import datetime
from typing import TextIO
from ..core.models import ScanResult, ProtectionStatus, GlobalConfig
from .. import __version__


class HTMLOutput:
    """HTML report generator"""
    
    def __init__(self, config: GlobalConfig):
        self.config = config
    
    def output(self, result: ScanResult, file: TextIO = None):
        """Generate HTML report"""
        if file is None:
            if self.config.report_file:
                file = open(self.config.report_file, 'w')
            else:
                file = sys.stdout
        
        try:
            html = self._generate_html(result)
            file.write(html)
        finally:
            if file != sys.stdout:
                file.close()
    
    def _generate_html(self, result: ScanResult) -> str:
        """Generate complete HTML report"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slowloris Check Report - {result.target_url}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header(result)}
        {self._generate_summary(result)}
        {self._generate_port_details(result)}
        {self._generate_recommendations(result)}
        {self._generate_footer(result)}
    </div>
</body>
</html>"""
    
    def _get_css(self) -> str:
        """Get CSS styles"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .section {
            padding: 40px;
            border-bottom: 1px solid #eee;
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        .section h2 {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #667eea;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .summary-card h3 {
            font-size: 0.9em;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 10px;
        }
        
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        
        .status-excellent { color: #28a745; }
        .status-good { color: #5cb85c; }
        .status-moderate { color: #ffc107; }
        .status-weak { color: #ff9800; }
        .status-vulnerable { color: #dc3545; }
        
        .score-bar {
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .score-fill {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 1s ease;
        }
        
        .score-excellent { background: linear-gradient(90deg, #28a745, #5cb85c); }
        .score-good { background: linear-gradient(90deg, #5cb85c, #8bc34a); }
        .score-moderate { background: linear-gradient(90deg, #ffc107, #ff9800); }
        .score-weak { background: linear-gradient(90deg, #ff9800, #ff5722); }
        .score-vulnerable { background: linear-gradient(90deg, #dc3545, #c82333); }
        
        .port-grid {
            display: grid;
            gap: 20px;
        }
        
        .port-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .port-card h3 {
            font-size: 1.5em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .port-status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-excellent-bg { background: #28a745; color: white; }
        .status-good-bg { background: #5cb85c; color: white; }
        .status-moderate-bg { background: #ffc107; color: #333; }
        .status-weak-bg { background: #ff9800; color: white; }
        .status-vulnerable-bg { background: #dc3545; color: white; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        
        .stat-value {
            font-weight: bold;
            color: #333;
        }
        
        .recommendations {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            border-radius: 4px;
        }
        
        .recommendations h3 {
            color: #856404;
            margin-bottom: 15px;
        }
        
        .recommendations ul {
            list-style: none;
            padding-left: 0;
        }
        
        .recommendations li {
            padding: 10px 0;
            padding-left: 25px;
            position: relative;
        }
        
        .recommendations li:before {
            content: "→";
            position: absolute;
            left: 0;
            color: #ffc107;
            font-weight: bold;
        }
        
        .footer {
            background: #f8f9fa;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        
        .metadata {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 20px;
            font-size: 0.9em;
        }
        
        .metadata-item {
            display: flex;
            gap: 10px;
        }
        
        .metadata-label {
            font-weight: bold;
            color: #666;
        }
        """
    
    def _generate_header(self, result: ScanResult) -> str:
        """Generate header section"""
        return f"""
        <div class="header">
            <h1>🛡️ Slowloris Security Assessment</h1>
            <div class="subtitle">{result.target_url}</div>
        </div>
        """
    
    def _generate_summary(self, result: ScanResult) -> str:
        """Generate summary section"""
        status_class = f"status-{result.overall_status.value}"
        score_class = f"score-{result.overall_status.value}"
        
        return f"""
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary">
                <div class="summary-card">
                    <h3>Overall Score</h3>
                    <div class="value {status_class}">{result.overall_score:.1f}/100</div>
                </div>
                <div class="summary-card">
                    <h3>Protection Status</h3>
                    <div class="value {status_class}">{result.overall_status.value.upper()}</div>
                </div>
                <div class="summary-card">
                    <h3>Ports Scanned</h3>
                    <div class="value">{len(result.port_results)}</div>
                </div>
                <div class="summary-card">
                    <h3>Scan Duration</h3>
                    <div class="value">{result.duration:.1f}s</div>
                </div>
            </div>
            
            <div class="score-bar">
                <div class="score-fill {score_class}" style="width: {result.overall_score}%">
                    {result.overall_score:.1f}%
                </div>
            </div>
            
            <div class="metadata">
                <div class="metadata-item">
                    <span class="metadata-label">Target IP:</span>
                    <span>{result.target_ip}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Scan ID:</span>
                    <span>{result.scan_id}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Started:</span>
                    <span>{result.started_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Completed:</span>
                    <span>{result.completed_at.strftime('%Y-%m-%d %H:%M:%S') if result.completed_at else 'N/A'}</span>
                </div>
            </div>
        </div>
        """
    
    def _generate_port_details(self, result: ScanResult) -> str:
        """Generate port details section"""
        ports_html = []
        
        for port, port_result in sorted(result.port_results.items()):
            status_class = f"status-{port_result.status.value}"
            status_bg_class = f"status-{port_result.status.value}-bg"
            score_class = f"score-{port_result.status.value}"
            
            ports_html.append(f"""
            <div class="port-card">
                <h3>
                    Port {port}
                    <span class="port-status {status_bg_class}">{port_result.status.value}</span>
                </h3>
                
                <div class="score-bar">
                    <div class="score-fill {score_class}" style="width: {port_result.protection_score}%">
                        {port_result.protection_score:.1f}/100
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Total Connections:</span>
                        <span class="stat-value">{port_result.total_connections}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Successful:</span>
                        <span class="stat-value">{port_result.successful_connections}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Failed:</span>
                        <span class="stat-value">{port_result.failed_connections}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Kept Open:</span>
                        <span class="stat-value">{port_result.kept_open_count} ({port_result.kept_open_rate:.1f}%)</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Median Duration:</span>
                        <span class="stat-value">{port_result.median_duration:.1f}s</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Mean Duration:</span>
                        <span class="stat-value">{port_result.mean_duration:.1f}s</span>
                    </div>
                </div>
            </div>
            """)
        
        return f"""
        <div class="section">
            <h2>Port Analysis</h2>
            <div class="port-grid">
                {''.join(ports_html)}
            </div>
        </div>
        """
    
    def _generate_recommendations(self, result: ScanResult) -> str:
        """Generate recommendations section"""
        recommendations = []
        
        if result.overall_score >= 90:
            intro = "✓ Excellent! Your server has strong protection against Slowloris attacks."
        elif result.overall_score >= 70:
            intro = "✓ Good protection, but there's room for improvement."
        else:
            intro = "⚠️ Your server needs better protection against Slowloris attacks."
        
        for port, port_result in result.port_results.items():
            if port_result.protection_score < 70:
                recommendations.append(
                    f"Configure shorter header timeout for port {port} "
                    f"(current median: {port_result.median_duration:.1f}s)"
                )
        
        recommendations.extend([
            "Configure client_header_timeout (Nginx) or RequestReadTimeout (Apache)",
            "Implement rate limiting per IP address",
            "Consider using a WAF (Web Application Firewall)",
            "Monitor connection pool usage and set appropriate limits",
            "Keep your web server software up to date"
        ])
        
        recs_html = '\n'.join(f"<li>{rec}</li>" for rec in recommendations)
        
        return f"""
        <div class="section">
            <h2>Recommendations</h2>
            <div class="recommendations">
                <h3>{intro}</h3>
                <ul>
                    {recs_html}
                </ul>
            </div>
        </div>
        """
    
    def _generate_footer(self, result: ScanResult) -> str:
        """Generate footer section"""
        return f"""
        <div class="footer">
            <p>Generated by Slowloris Checker v{__version__}</p>
            <p>Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>⚠️ This tool should only be used on systems you own or have permission to test.</p>
        </div>
        """
