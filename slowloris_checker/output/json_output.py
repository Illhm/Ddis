"""
JSON output handler
"""

import json
import sys
from typing import TextIO
from ..core.models import ScanResult, GlobalConfig


class JSONOutput:
    """JSON output handler"""
    
    def __init__(self, config: GlobalConfig):
        self.config = config
    
    def output(self, result: ScanResult, file: TextIO = None):
        """Output scan result as JSON"""
        if file is None:
            if self.config.output_file:
                file = open(self.config.output_file, 'w')
            else:
                file = sys.stdout
        
        try:
            data = result.to_dict()
            json.dump(data, file, indent=2)
            if file == sys.stdout:
                print()  # Add newline for console output
        finally:
            if file != sys.stdout:
                file.close()
