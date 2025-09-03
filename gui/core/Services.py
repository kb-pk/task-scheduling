"""
Threading and method execution services for the application.
"""
import logging
import threading
import queue
import traceback
from typing import Dict, Any, Callable, Optional, Set
from concurrent.futures import ThreadPoolExecutor, Future
import time

from scheduler.methods.BaseMethod import BaseMethod
from .Interfaces import MethodRunner, DataProcessor
from ..config import ThreadingConfig, ApplicationMessages


logger = logging.getLogger(__name__)


class MethodExecutionService(MethodRunner):
    """Professional service for running optimization methods."""
    
    def __init__(self, config: ThreadingConfig, data_processor: DataProcessor):
        self.config = config
        self.data_processor = data_processor
        self._executor = ThreadPoolExecutor(
            max_workers=config.max_concurrent_methods,
            thread_name_prefix="MethodRunner"
        )
        self._running_futures: Set[Future] = set()
        self._current_method: Optional[BaseMethod] = None
        self._lock = threading.Lock()
    
    def run_method(self, method: BaseMethod, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Run a method asynchronously and call callback with results."""
        if self.is_running():
            callback({"error": ApplicationMessages.METHOD_ALREADY_RUNNING, "success": False})
            return
        
        with self._lock:
            self._current_method = method
            future = self._executor.submit(self._execute_method, method)
            self._running_futures.add(future)
            
            # Setup completion callback
            future.add_done_callback(lambda f: self._handle_completion(f, callback))
    
    def is_running(self) -> bool:
        """Check if a method is currently running."""
        with self._lock:
            # Clean up completed futures
            self._running_futures = {f for f in self._running_futures if not f.done()}
            return len(self._running_futures) > 0
    
    def cancel_current_run(self) -> bool:
        """Cancel the currently running method if any."""
        with self._lock:
            if not self._running_futures:
                return False
            
            # Cancel all running futures
            cancelled = False
            for future in self._running_futures:
                if future.cancel():
                    cancelled = True
            
            if cancelled:
                self._current_method = None
                logger.info("Method execution cancelled")
            
            return cancelled
    
    def shutdown(self) -> None:
        """Shutdown the execution service gracefully."""
        logger.info("Shutting down method execution service...")
        
        # Cancel all running methods
        self.cancel_current_run()
        
        # Shutdown executor (timeout parameter added in Python 3.9+)
        try:
            self._executor.shutdown(wait=True, timeout=5.0)
        except TypeError:
            # Fallback for older Python versions
            self._executor.shutdown(wait=True)
        logger.info("Method execution service shutdown complete")
    
    def _execute_method(self, method: BaseMethod) -> Dict[str, Any]:
        """Execute a method and return results."""
        try:
            start_time = time.time()
            logger.info(f"Starting execution of {method.get_name()}")
            
            # Run the method
            method.run()
            
            # Process results
            result = self.data_processor.process_method_results(method)
            result["success"] = True
            result["execution_time"] = time.time() - start_time
            
            logger.info(f"Method {method.get_name()} completed successfully in {result['execution_time']:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Method execution failed: {e}")
            logger.error(traceback.format_exc())
            return {
                "error": str(e),
                "success": False,
                "traceback": traceback.format_exc()
            }
    
    def _handle_completion(self, future: Future, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Handle completion of method execution."""
        try:
            with self._lock:
                self._running_futures.discard(future)
                self._current_method = None
            
            # Get result and call callback
            try:
                result = future.result()
            except Exception as e:
                result = {
                    "error": f"Future execution failed: {e}",
                    "success": False,
                    "traceback": traceback.format_exc()
                }
            
            callback(result)
            
        except Exception as e:
            logger.error(f"Error in completion handler: {e}")
            callback({
                "error": f"Completion handler failed: {e}",
                "success": False
            })


class ResultDataProcessor(DataProcessor):
    """Processes method results into UI-ready data structures."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_method_results(self, method: BaseMethod) -> Dict[str, Any]:
        """Process method results into structured data for UI."""
        try:
            # Get the best solution
            best_solution = method.get_best_solution()
            if not best_solution:
                raise ValueError("Could not get schedule map from best solution")
            
            # Process schedule map with timing information
            schedule_map = self._process_schedule_map(method, best_solution)
            
            # Process history data
            history_data = self._process_history_data(method)
            
            # Get machine names
            machine_names = [f"M{i}" for i in range(len(method.machines))]
            
            result = {
                "schedule_map": schedule_map,
                "machine_names": machine_names,
                **history_data
            }
            
            self.logger.info(f"Successfully processed results for {method.get_name()}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process method results: {e}")
            raise
    
    def _process_schedule_map(self, method: BaseMethod, best_solution: Dict[str, Any]) -> Dict[str, Any]:
        """Process schedule map with detailed timing information."""
        schedule_map = best_solution
        schedule_map_details = {}
        
        if schedule_map:
            for machine_id, task_ids in schedule_map.items():
                detailed_tasks = []
                current_time = 0.0
                
                # Ensure task_ids is always iterable
                if not isinstance(task_ids, (list, tuple)):
                    import numpy as np
                    if isinstance(task_ids, np.ndarray):
                        task_ids = task_ids.tolist()
                    else:
                        task_ids = [task_ids] if task_ids is not None else []
                
                for task_id in task_ids:
                    try:
                        duration = method.etc[task_id][machine_id]
                        detailed_tasks.append((task_id, current_time, duration))
                        current_time += duration
                    except (IndexError, KeyError) as e:
                        self.logger.warning(f"Could not get duration for task {task_id} on machine {machine_id}: {e}")
                        continue
                
                schedule_map_details[machine_id] = detailed_tasks
        
        return schedule_map_details
    
    def _process_history_data(self, method: BaseMethod) -> Dict[str, Any]:
        """Process historical fitness data."""
        history_makespan, history_energy = [], []
        
        try:
            history_fn = getattr(method, 'get_history', None)
            if callable(history_fn):
                history_fitness = history_fn()
                if isinstance(history_fitness, list):
                    for fit in history_fitness:
                        if fit and hasattr(fit, 'get_all'):
                            metrics = fit.get_all()
                            if isinstance(metrics, dict):
                                # Import here to avoid circular imports
                                from scheduler.ProgramState import ProgramState
                                state_enum = ProgramState._ProgramState__SchedulingState.State
                                
                                makespan_val = metrics.get(state_enum.makespan)
                                energy_val = metrics.get(state_enum.energy)
                                
                                if makespan_val is not None:
                                    history_makespan.append(makespan_val)
                                if energy_val is not None:
                                    history_energy.append(energy_val)
        
        except Exception as e:
            self.logger.warning(f"Could not process history data: {e}")
        
        return {
            "history_makespan": history_makespan,
            "history_energy": history_energy
        }
