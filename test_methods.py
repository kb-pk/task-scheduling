#!/usr/bin/env python3
"""Test script to check method registration."""

# Import all methods to trigger registration
from scheduler.methods.Michigan import MichiganMethod
from scheduler.methods.Pitt_direct import PittDirectMethod
from scheduler.methods.Pitt_perm import PittPermMethod
from scheduler.methods.Dragonfly import DragonflyMethod
from scheduler.methods.Fruitfly import FruitflyMethod

from scheduler.Registry import MethodRegistry
from scheduler.ProgramState import ProgramState
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from lang.Lang import T

def test_registry():
    print("=== METHOD REGISTRY TEST ===")
    
    registry = MethodRegistry.get_registry()
    print(f"Registry has {len(registry)} methods:")
    for name, cls in registry.items():
        print(f"  - {name}: {cls}")
    
    print("\n=== METHOD INSTANTIATION TEST ===")
    
    state = ProgramState()
    t = T(state)
    logger = Logger(state, print)
    cache = MethodCache()
    
    methods = {}
    for name, cls in registry.items():
        try:
            instance = cls(state, logger, t, cache)
            methods[name] = instance
            print(f"✓ Successfully instantiated {name}")
        except Exception as e:
            print(f"✗ Failed to instantiate {name}: {e}")
    
    print(f"\nTotal instantiated methods: {len(methods)}")
    return methods

if __name__ == "__main__":
    test_registry()
