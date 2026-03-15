"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Phantom Documentation Kit - Logging System
Provides dual-output logging with console and timestamped file output
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json
import re

class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ConsoleFormatter(logging.Formatter):
    """Simple formatter for console output without colors"""
    
    def __init__(self):
        super().__init__(fmt='%(levelname)-8s %(message)s')
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output"""
        # Use parent formatter
        formatted = super().format(record)
        
        # Add exception info if present
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)
            
        return formatted


class FileFormatter(logging.Formatter):
    """Custom formatter for file output with timestamps"""
    
    def __init__(self, timestamp_format: str = '%Y-%m-%d %H:%M:%S'):
        self.timestamp_format = timestamp_format
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for file output"""
        # Strip ANSI color codes from message
        message = self._strip_ansi_codes(record.getMessage())
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime(self.timestamp_format)
        
        # Build log entry
        parts = [
            timestamp,
            f"[{record.levelname}]",
            f"[{record.name}]",
            message
        ]
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            extra = json.dumps(record.extra_fields, ensure_ascii=False)
            parts.append(f"| {extra}")
        
        formatted = ' '.join(parts)
        
        # Add exception info if present
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)
            
        return formatted
    
    @staticmethod
    def _strip_ansi_codes(text: str) -> str:
        """Remove ANSI color codes from text"""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)


class PhantomLogger:
    """Main logger class for Phantom Documentation Kit"""
    
    _instances: Dict[str, 'PhantomLogger'] = {}
    _config: Optional[Dict[str, Any]] = None
    _log_dir: Optional[Path] = None
    _session_initialized = False
    _session_log_file: Optional[Path] = None
    _session_timestamp: Optional[datetime] = None
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    @classmethod
    def load_config(cls, config: Dict[str, Any]) -> None:
        """Load logging configuration"""
        cls._config = config.get('logging', {
            'enabled': True,
            'console_level': 'INFO',
            'file_level': 'DEBUG',
            'log_directory': 'logs',
            'max_file_size': '10MB',
            'backup_count': 5,
            'timestamp_format': '%Y-%m-%d %H:%M:%S'
        })
        
        # Disable file logging in Docker container mode
        if os.environ.get('DOCKER_MODE') == '1':
            cls._config['enabled'] = False
            return
            
        # Create log directory if file logging is enabled
        if cls._config.get('enabled', True):
            # Always use absolute path from project root
            log_dir_config = cls._config.get('log_directory', 'logs')
            # Find project root (where config.json is)
            project_root = Path.cwd()
            while project_root != project_root.parent:
                if (project_root / 'config.json').exists():
                    break
                project_root = project_root.parent
            
            # Create absolute log directory path
            cls._log_dir = project_root / log_dir_config
            try:
                cls._log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                # If we can't create log dir, disable file logging
                print(f"Warning: Could not create log directory: {e}")
                cls._config['enabled'] = False
    
    def _setup_logger(self) -> None:
        """Set up logger with handlers"""
        # Clear any existing handlers
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
        
        # Always add console handler
        self._add_console_handler()
        
        # Add file handler if enabled
        if self._config and self._config.get('enabled', True) and self._log_dir:
            self._add_file_handler()
    
    def _add_console_handler(self) -> None:
        """Add console handler with simple text output"""
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Get console log level from config or environment
        console_level = os.environ.get('PHANTOM_LOG_LEVEL', 
                                     self._config.get('console_level', 'INFO') if self._config else 'INFO')
        console_handler.setLevel(getattr(logging, console_level.upper()))
        
        # Set simple console formatter
        console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self) -> None:
        """Add rotating file handler"""
        try:
            # Use existing session log file if already initialized
            if PhantomLogger._session_initialized and PhantomLogger._session_log_file:
                log_file = PhantomLogger._session_log_file
            else:
                # Use session timestamp (create once per session)
                if PhantomLogger._session_timestamp is None:
                    PhantomLogger._session_timestamp = datetime.now()
                
                # Determine log filename with session timestamp
                mode = 'serve' if 'serve' in sys.argv[0] else 'build'
                timestamp = PhantomLogger._session_timestamp
                date_str = timestamp.strftime('%Y%m%d')
                time_str = timestamp.strftime('%H%M%S')
                
                # Use pattern from config or create session-based filename
                filename_pattern = self._config.get('log_filename_pattern', 'phantom-{mode}-{date}-{time}.log')
                filename = filename_pattern.format(mode=mode, date=date_str, time=time_str)
                log_file = self._log_dir / filename
                
                # Store session log file for other loggers to use
                PhantomLogger._session_log_file = log_file
            
            # Parse max file size
            max_size_str = self._config.get('max_file_size', '10MB')
            max_bytes = self._parse_size(max_size_str)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=self._config.get('backup_count', 5),
                encoding='utf-8'
            )
            
            # Set file log level
            file_level = self._config.get('file_level', 'DEBUG')
            file_handler.setLevel(getattr(logging, file_level.upper()))
            
            # Set file formatter
            timestamp_format = self._config.get('timestamp_format', '%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(FileFormatter(timestamp_format))
            
            self.logger.addHandler(file_handler)
            
            # Write session header only once per session
            if not PhantomLogger._session_initialized:
                mode = 'serve' if 'serve' in sys.argv[0] else 'build'
                # Use the same session timestamp
                timestamp = PhantomLogger._session_timestamp
                self._write_session_header(log_file, mode, timestamp)
                PhantomLogger._session_initialized = True
                
                # Log file creation info
                print(f"INFO     Log file created: {log_file.name}")
            
        except Exception as e:
            # Log error but don't fail
            print(f"Warning: Could not set up file logging: {e}")
    
    def _write_session_header(self, log_file: Path, mode: str, timestamp: datetime) -> None:
        """Write session information header to the log file"""
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"PHANTOM DOCUMENTATION KIT - SESSION LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Session Start Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Mode: {mode.upper()}\n")
                f.write(f"Log Level (Console): {self._config.get('console_level', 'INFO')}\n")
                f.write(f"Log Level (File): {self._config.get('file_level', 'DEBUG')}\n")
                f.write(f"Command: {' '.join(sys.argv)}\n")
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"Warning: Could not write session header: {e}")
    
    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        size_str = size_str.strip().upper()
        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                try:
                    number = float(size_str[:-len(unit)])
                    return int(number * multiplier)
                except ValueError:
                    pass
        
        # Default to 10MB if parsing fails
        return 10 * 1024 * 1024
    
    def _log_with_extra(self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None, 
                       exc_info: bool = False) -> None:
        """Internal method to log with extra fields"""
        log_record_extra = {}
        if extra:
            log_record_extra['extra_fields'] = extra
        
        self.logger.log(level, msg, exc_info=exc_info, extra=log_record_extra)
    
    # Public logging methods
    def debug(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message"""
        self._log_with_extra(logging.DEBUG, msg, extra)
    
    def info(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message"""
        self._log_with_extra(logging.INFO, msg, extra)
    
    def warning(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message"""
        self._log_with_extra(logging.WARNING, msg, extra)
    
    def error(self, msg: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> None:
        """Log error message"""
        self._log_with_extra(logging.ERROR, msg, extra, exc_info=exc_info)
    
    def critical(self, msg: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> None:
        """Log critical message"""
        self._log_with_extra(logging.CRITICAL, msg, extra, exc_info=exc_info)


# Module-level functions for easy access
def get_logger(name: str) -> PhantomLogger:
    """Get or create a logger instance"""
    # noinspection PyProtectedMember
    if name not in PhantomLogger._instances:
        # noinspection PyProtectedMember
        PhantomLogger._instances[name] = PhantomLogger(name)
    # noinspection PyProtectedMember
    return PhantomLogger._instances[name]


def init_logging(config: Dict[str, Any]) -> None:
    """Initialize logging system with configuration"""
    PhantomLogger.load_config(config)
    
    # Re-setup all existing loggers with new config
    # noinspection PyProtectedMember
    for logger in PhantomLogger._instances.values():
        # noinspection PyProtectedMember
        logger._setup_logger()


# Convenience function for backward compatibility
def log_info(msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Log info message using default logger"""
    logger = get_logger('phantom')
    logger.info(msg, extra)