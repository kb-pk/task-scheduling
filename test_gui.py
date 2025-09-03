#!/usr/bin/env python3
"""
Quick test script to verify the Task Scheduling GUI application works.
"""
import sys
import os

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from gui.app import run, TaskSchedulingGUI, GUI
        print("✓ Successfully imported main app components")
        
        from gui.TaskSchedulingGUI import TaskSchedulingGUI as DirectGUI
        print("✓ Successfully imported TaskSchedulingGUI directly")
        
        # Test that aliases work
        assert GUI == TaskSchedulingGUI, "GUI alias should point to TaskSchedulingGUI"
        assert DirectGUI == TaskSchedulingGUI, "Direct import should match app import"
        print("✓ All aliases work correctly")
        
        print("All imports successful!")
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_application_creation():
    """Test that the application can be created without errors."""
    print("\nTesting application creation...")
    
    try:
        from scheduler.ProgramState import ProgramState
        from scheduler.methods.Michigan import MichiganMethod
        from scheduler.Logger import Logger
        from lang.Lang import T
        from scheduler.MethodCache import MethodCache
        from gui.TaskSchedulingGUI import TaskSchedulingGUI
        from gui.app_config import ApplicationConfig
        
        # Create required dependencies
        state = ProgramState()
        t = T(state)
        scheduler_logger = Logger(state, lambda msg: print(msg, end=''))
        cache = MethodCache()
        
        # Create a test method
        method = MichiganMethod(state, scheduler_logger, t, cache)
        methods = {"Michigan": method}
        
        # Create config
        config = ApplicationConfig()
        
        # Create GUI (but don't start it)
        gui = TaskSchedulingGUI(state, t, methods, config)
        print("✓ TaskSchedulingGUI created successfully")
        
        # Clean up
        gui.destroy()
        print("✓ TaskSchedulingGUI destroyed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Application creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Task Scheduling GUI Application Test")
    print("=" * 40)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test application creation
    if not test_application_creation():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("✓ All tests passed! The application is ready to run.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)
