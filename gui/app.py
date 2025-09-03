"""
Main application entry point for Task Scheduling Application.
This maintains backward compatibility while using the new clean architecture.
"""
import logging
from typing import Dict

from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod

from .TaskSchedulingGUI import TaskSchedulingGUI
from .config import ApplicationConfig


# Setup logging with proper line breaks
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Backward compatibility - export as GUI
GUI = TaskSchedulingGUI


def run() -> None:
    """Run the task scheduling application with professional architecture."""
    from scheduler.MethodCache import MethodCache
    from scheduler.Logger import Logger
    from scheduler.Registry import MethodRegistry
    from lang.Lang import T
    
    # CRITICAL: Import all method classes to trigger registration decorators
    # Without these imports, the classes won't be registered in MethodRegistry!
    from scheduler.methods.Michigan import MichiganMethod
    from scheduler.methods.Pitt_direct import PittDirectMethod
    from scheduler.methods.Pitt_perm import PittPermMethod
    from scheduler.methods.Dragonfly import DragonflyMethod
    from scheduler.methods.Fruitfly import FruitflyMethod
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Task Scheduling Application...")
    
    try:
        # Initialize core components
        state = ProgramState()
        t = T(state)
        scheduler_logger = Logger(state, lambda msg: print(msg, end=''))  # Fix line breaks
        cache = MethodCache()

        # Instantiate methods
        methods: Dict[str, BaseMethod] = {}
        for name, cls in MethodRegistry.get_registry().items():
            try:
                methods[name] = cls(state, scheduler_logger, t, cache)
                logger.info(f"Successfully instantiated method: {name}")
            except Exception as e:
                logger.error(f"Failed to instantiate {name}: {e}")
        
        if not methods:
            raise RuntimeError("No methods were successfully instantiated")
        
        # Create and configure application
        config = ApplicationConfig()
        app = TaskSchedulingGUI(state, t, methods, config)
        
        # Connect scheduler logger to app
        scheduler_logger.set_log_fn(app.log)
        
        # Start application
        app.start()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


if __name__ == "__main__":
    run()