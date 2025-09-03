import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
import threading
import queue
import numpy as np

from scheduler.Registry import UIRegistrator
from scheduler.UI import UI
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod

from .Sidebar import Sidebar
from .MainContent import MainContent

@UIRegistrator.register_class
class GUI(tk.Tk, UI):
    def __init__(self, state: ProgramState, t, method_instances: Dict[str, BaseMethod]) -> None:
        self.state = state
        self.T = t
        self.method_instances = method_instances
        self._is_running = False
        self._result_queue = queue.Queue()

        super().__init__()
        self.title("Task Scheduling")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(0, self._center_initial_window)

        self.columnconfigure(0, weight=0, minsize=360)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = Sidebar(
            self,
            state=self.state,
            method_instances=self.method_instances,
            on_start_clicked=self._on_start_clicked,
            on_objective_changed=self._on_objective_changed,
            width=360
        )
        self.main_content = MainContent(self)

    def _center_initial_window(self) -> None:
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w = max(960, int(sw * 0.6))
            h = max(720, int(sh * 0.6))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def log(self, message):
        self.main_content.log(f"{message}\n")

    def start(self):
        self.mainloop()

    def _on_closing(self):
        if self._is_running:
            # Optionally, ask the user if they are sure
            pass
        self.destroy()

    def _on_objective_changed(self, new_objective: str):
        self.log(f"Objective changed to: {new_objective}")
        state_enum = ProgramState._ProgramState__SchedulingState.State
        if new_objective == "MAKESPAN":
            self.state.scheduling.set(state_enum.makespan)
        else:
            self.state.scheduling.set(state_enum.energy)

    def _on_start_clicked(self):
        if self._is_running:
            self.log("An algorithm is already running.")
            return

        method = self.sidebar.get_selected_method()
        if not method:
            self.log("Error: No method selected.")
            return

        self.log(f"Starting method: {method.get_name()}...")
        
        warnings = self.sidebar.apply_parameters_to_method(method)
        for warning in warnings:
            self.log(f"Warning: {warning}")

        self.main_content.clear_plots()
        self._is_running = True
        self.sidebar.disable_start_button()

        # Run method in a separate thread
        thread = threading.Thread(target=self._run_method_thread, args=(method,), daemon=True)
        thread.start()
        self.after(100, self._check_result_queue)

    def _run_method_thread(self, method: BaseMethod):
        """Worker function to run in a separate thread."""
        try:
            method.run()
            
            # --- Data Preparation Stage ---
            best_solution = method.get_best_solution()

            # 1. For all evolutionary methods, best_solution is already a schedule_map
            # because both Michigan and EvolAlgoBaseMethod store the result of build_schedule_map
            schedule_map = best_solution

            if not schedule_map:
                raise ValueError("Could not get schedule map from best solution")

            # 2. Create detailed Gantt chart data with timing information
            schedule_map_details = {}
            if schedule_map:
                for machine_id, task_ids in schedule_map.items():
                    detailed_tasks = []
                    current_time = 0.0
                    # Ensure task_ids is always a list (handle different method outputs)
                    if not isinstance(task_ids, (list, tuple, np.ndarray)):
                        task_ids = [task_ids] if task_ids is not None else []
                    
                    for task_id in task_ids:
                        duration = method.etc[task_id][machine_id]
                        detailed_tasks.append((task_id, current_time, duration))
                        current_time += duration
                    schedule_map_details[machine_id] = detailed_tasks

            # 3. Get history data from list[IndividualFitness] using get_all()
            history_makespan, history_energy = [], []
            history_fn = getattr(method, 'get_history', None)
            if callable(history_fn):
                history_fitness = history_fn()
                if isinstance(history_fitness, list):
                    for fit in history_fitness:
                        if fit and hasattr(fit, 'get_all'):
                            metrics = fit.get_all()
                            if isinstance(metrics, dict):
                                history_makespan.append(metrics.get(self.state.scheduling.State.makespan))
                                history_energy.append(metrics.get(self.state.scheduling.State.energy))
            
            # Filter out any None values that might have appeared
            history_makespan = [v for v in history_makespan if v is not None]
            history_energy = [v for v in history_energy if v is not None]

            # 4. Prepare the final result package for the UI thread
            result = {
                "schedule_map": schedule_map_details,
                "machine_names": [f"M{i}" for i in range(len(method.machines))],
                "history_makespan": history_makespan,
                "history_energy": history_energy,
                "success": True
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = {"error": str(e), "success": False}
        self._result_queue.put(result)

    def _check_result_queue(self):
        """Check if the worker thread has finished."""
        try:
            result = self._result_queue.get_nowait()
            self._is_running = False
            self.sidebar.enable_start_button()

            if result.get("success"):
                self.log("Method execution finished.")
                self.main_content.render_plots(result)
            else:
                self.log(f"Error during method execution: {result.get('error')}")

        except queue.Empty:
            # Not finished yet, check again later
            self.after(100, self._check_result_queue)

def run() -> None:
    from scheduler.MethodCache import MethodCache
    from scheduler.Logger import Logger
    from scheduler.Registry import MethodRegistry
    from lang.Lang import T
    
    state = ProgramState()
    t = T(state)
    logger = Logger(state, print)
    cache = MethodCache()

    methods: Dict[str, BaseMethod] = {}
    for name, cls in MethodRegistry.get_registry().items():
        try:
            methods[name] = cls(state, logger, t, cache)
        except Exception as e:
            print(f"Failed to instantiate {name}: {e}")

    app = GUI(state, t, methods)
    logger.set_log_fn(app.log)
    app.start()

if __name__ == "__main__":
    run()