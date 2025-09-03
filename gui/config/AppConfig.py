"""
Configuration for the main application.
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class WindowConfig:
    """Configuration for the main application window."""
    
    title: str = "Task Scheduling"
    min_width: int = 960
    min_height: int = 720
    default_width_ratio: float = 0.6
    default_height_ratio: float = 0.6
    sidebar_width: int = 360
    sidebar_min_size: int = 360
    center_on_startup: bool = True


@dataclass(frozen=True)
class ThreadingConfig:
    """Configuration for threading behavior."""
    
    result_check_interval_ms: int = 100
    max_concurrent_methods: int = 1
    thread_timeout_seconds: Optional[float] = None
    daemon_threads: bool = True


@dataclass(frozen=True)
class UIConfig:
    """Configuration for UI behavior."""
    
    auto_clear_plots_on_start: bool = True
    show_warnings_in_log: bool = True
    show_progress_indicators: bool = True
    confirm_exit_when_running: bool = True


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for logging behavior."""
    
    log_level: str = "INFO"
    log_to_console: bool = True
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    max_log_lines: int = 1000


@dataclass
class ApplicationConfig:
    """Main configuration container for the application."""
    
    window: WindowConfig = WindowConfig()
    threading: ThreadingConfig = ThreadingConfig()
    ui: UIConfig = UIConfig()
    logging: LoggingConfig = LoggingConfig()
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.window.min_width < 640:
            raise ValueError("Minimum width must be at least 640 pixels")
        if self.window.min_height < 480:
            raise ValueError("Minimum height must be at least 480 pixels")
        if self.threading.result_check_interval_ms <= 0:
            raise ValueError("Result check interval must be positive")
        if self.threading.max_concurrent_methods < 1:
            raise ValueError("Max concurrent methods must be at least 1")


@dataclass(frozen=True)
class ApplicationMessages:
    """Messages used throughout the application."""
    
    # Startup messages
    STARTING_APPLICATION: str = "Starting Task Scheduling Application..."
    APPLICATION_READY: str = "Application ready."
    
    # Method execution messages
    METHOD_STARTING: str = "Starting method: {method_name}..."
    METHOD_COMPLETED: str = "Method execution finished."
    METHOD_FAILED: str = "Method execution failed: {error}"
    METHOD_ALREADY_RUNNING: str = "An algorithm is already running."
    NO_METHOD_SELECTED: str = "Error: No method selected."
    
    # Objective change messages
    OBJECTIVE_CHANGED: str = "Objective changed to: {objective}"
    
    # Warning messages
    PARAMETER_WARNING: str = "Warning: {warning}"
    
    # Shutdown messages
    SHUTTING_DOWN: str = "Shutting down application..."
    UNSAVED_WORK_WARNING: str = "Method is still running. Are you sure you want to exit?"
    
    # Error messages
    WINDOW_SETUP_ERROR: str = "Failed to setup window geometry"
    METHOD_INSTANTIATION_ERROR: str = "Failed to instantiate {method_name}: {error}"
    UNEXPECTED_ERROR: str = "Unexpected error: {error}"
