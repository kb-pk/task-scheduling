import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import StrMethodFormatter
import matplotlib.cm as cm

class MainContent(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, padding=(10, 10), **kwargs)
        self.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._main_nb = ttk.Notebook(self)
        self._main_nb.grid(row=0, column=0, sticky="nsew")

        # Gantt tab with sub-tabs
        self._tab_gantt = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_gantt, text="Gantt")
        self._nb_gantt = ttk.Notebook(self._tab_gantt)
        self._nb_gantt.pack(fill="both", expand=True)
        self._gantt_makespan = ttk.Frame(self._nb_gantt)
        self._gantt_energy = ttk.Frame(self._nb_gantt)
        self._nb_gantt.add(self._gantt_makespan, text="Makespan")
        self._nb_gantt.add(self._gantt_energy, text="Energy")

        # Linear tab with sub-tabs
        self._tab_linear = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_linear, text="Linear")
        self._nb_linear = ttk.Notebook(self._tab_linear)
        self._nb_linear.pack(fill="both", expand=True)
        self._linear_makespan = ttk.Frame(self._nb_linear)
        self._linear_energy = ttk.Frame(self._nb_linear)
        self._nb_linear.add(self._linear_makespan, text="Makespan")
        self._nb_linear.add(self._linear_energy, text="Energy")
        
        # Diagnostics tab
        self._tab_diag = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_diag, text="Diagnostics")
        self._diag_text = tk.Text(self._tab_diag, wrap="word", state="disabled", height=10, font=("Consolas", 9))
        self._diag_scroll = ttk.Scrollbar(self._tab_diag, orient="vertical", command=self._diag_text.yview)
        self._diag_text.configure(yscrollcommand=self._diag_scroll.set)
        self._diag_scroll.pack(side="right", fill="y")
        self._diag_text.pack(side="left", fill="both", expand=True)

        
        for frame in [self._gantt_makespan, self._gantt_energy, self._linear_makespan, self._linear_energy]:
            ttk.Label(frame, text="Matplotlib not found. Plots are disabled.").pack(pady=20)

    def log(self, message: str):
        self._diag_text.configure(state="normal")
        self._diag_text.insert("end", message)
        self._diag_text.configure(state="disabled")
        self._diag_text.see("end")

    def clear_plots(self):
        for frame in [self._gantt_makespan, self._gantt_energy, self._linear_makespan, self._linear_energy]:
            for widget in frame.winfo_children():
                widget.destroy()

    def render_plots(self, solution: Dict[str, Any]):
        self.clear_plots()
        
        # Gantt Charts - Different for each objective
        fig_gantt_makespan = self._create_gantt_makespan_figure(solution)
        self._draw_figure(self._gantt_makespan, fig_gantt_makespan)
        
        fig_gantt_energy = self._create_gantt_energy_figure(solution)
        self._draw_figure(self._gantt_energy, fig_gantt_energy)

        # Linear (fitness history) Charts
        fig_linear_makespan = self._create_linear_figure(solution.get("history_makespan", []), "Makespan History", "Makespan")
        self._draw_figure(self._linear_makespan, fig_linear_makespan)
        
        fig_linear_energy = self._create_linear_figure(solution.get("history_energy", []), "Energy History", "Energy")
        self._draw_figure(self._linear_energy, fig_linear_energy)

    def _draw_figure(self, parent: ttk.Frame, fig: Figure | None):
        if fig is None:
            ttk.Label(parent, text="No data to display.").pack()
            return
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _create_gantt_makespan_figure(self, solution: Dict[str, Any]) -> Figure | None:
        """Creates a Gantt chart with TIME on X-axis (makespan view)"""
        schedule_map = solution.get("schedule_map", {})
        machine_names = solution.get("machine_names", [])
        if not schedule_map: return None

        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)

        # Get all unique task IDs for consistent coloring
        all_task_ids = sorted(list(set(
            task_id for tasks in schedule_map.values() for task_id, _, _ in tasks
        )))

        if all_task_ids:
            colors = cm.get_cmap('viridis', len(all_task_ids))
            task_colors = {task_id: colors(i) for i, task_id in enumerate(all_task_ids)}
        else:
            task_colors = {}

        # Calculate makespan for the red line
        makespan = 0.0
        for machine_id, tasks in schedule_map.items():
            machine_end_time = 0.0
            for task_id, start_time, duration in tasks:
                machine_end_time = max(machine_end_time, start_time + duration)
            makespan = max(makespan, machine_end_time)

        # Draw time-based Gantt bars
        for machine_id, tasks in schedule_map.items():
            for task_id, start_time, duration in tasks:
                color = task_colors.get(task_id, 'gray')
                ax.barh(machine_id, duration, left=start_time, height=0.6, 
                       align='center', color=color, edgecolor='black')
                
                # Add task label if there's space
                if duration > makespan * 0.02:  # Only if bar is wide enough
                    ax.text(start_time + duration/2, machine_id, f'T{task_id}', 
                           ha='center', va='center', color='white', fontsize=8, weight='bold')

        # Add makespan line
        if makespan > 0:
            ax.axvline(makespan, color='red', linestyle='--', linewidth=1.2)
            ax.text(makespan, len(machine_names)-0.5, f'Makespan: {makespan:.1f}',
                   rotation=90, va='bottom', ha='left', color='red', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

        if machine_names:
            ax.set_yticks(range(len(machine_names)))
            ax.set_yticklabels(machine_names)
        
        ax.invert_yaxis()
        ax.set_xlabel("Time")
        ax.set_ylabel("Machine")
        ax.set_title("Gantt Chart - Makespan View")
        ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
        fig.tight_layout()
        return fig

    def _create_gantt_energy_figure(self, solution: Dict[str, Any]) -> Figure | None:
        """Creates a Gantt chart with ENERGY on X-axis (energy view)"""
        schedule_map = solution.get("schedule_map", {})
        machine_names = solution.get("machine_names", [])
        if not schedule_map: return None

        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)

        # Get all unique task IDs for consistent coloring
        all_task_ids = sorted(list(set(
            task_id for tasks in schedule_map.values() for task_id, _, _ in tasks
        )))

        if all_task_ids:
            colors = cm.get_cmap('viridis', len(all_task_ids))
            task_colors = {task_id: colors(i) for i, task_id in enumerate(all_task_ids)}
        else:
            task_colors = {}

        # Mock P_busy values (since we don't have access to actual machine data here)
        # In real implementation, this should come from solution data
        p_busy_base = 100  # Base power consumption
        
        # Calculate max busy energy for the red line
        max_busy_energy = 0.0
        for machine_id, tasks in schedule_map.items():
            machine_busy_energy = 0.0
            p_busy = p_busy_base + machine_id * 10  # Mock different power per machine
            for task_id, start_time, duration in tasks:
                task_energy = duration * p_busy
                machine_busy_energy += task_energy
            max_busy_energy = max(max_busy_energy, machine_busy_energy)

        # Draw energy-based Gantt bars
        for machine_id, tasks in schedule_map.items():
            current_energy = 0.0
            p_busy = p_busy_base + machine_id * 10  # Mock power value
            
            for task_id, start_time, duration in tasks:
                task_energy = duration * p_busy
                color = task_colors.get(task_id, 'gray')
                ax.barh(machine_id, task_energy, left=current_energy, height=0.6,
                       align='center', color=color, edgecolor='black')
                
                # Add task label if there's space
                if task_energy > max_busy_energy * 0.02:  # Only if bar is wide enough
                    ax.text(current_energy + task_energy/2, machine_id, f'T{task_id}',
                           ha='center', va='center', color='white', fontsize=8, weight='bold')
                
                current_energy += task_energy

        # Add max busy energy line
        if max_busy_energy > 0:
            ax.axvline(max_busy_energy, color='red', linestyle='--', linewidth=1.2)
            ax.text(max_busy_energy, len(machine_names)-0.5, f'Max Energy: {max_busy_energy:.1f}',
                   rotation=90, va='bottom', ha='left', color='red', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

        if machine_names:
            ax.set_yticks(range(len(machine_names)))
            ax.set_yticklabels(machine_names)
        
        ax.invert_yaxis()
        ax.set_xlabel("Energy")
        ax.set_ylabel("Machine")
        ax.set_title("Gantt Chart - Energy View")
        ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
        fig.tight_layout()
        return fig

    def _create_linear_figure(self, history: List, title: str, y_label: str) -> Figure | None:
        if not history: return None

        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        xs = list(range(len(history)))
        
        # Plot best-so-far as a step function to show progression
        ax.step(xs, history, where='post', linewidth=1.5, color="#1f77b4", label="Best so far")
        
        # Also plot individual points for clarity
        ax.plot(xs, history, marker='o', markersize=2, linewidth=1.2, color="#1f77b4")
        
        # Highlight epochs where the best value improved (decreased)
        change_x, change_y = [], []
        if history:
            prev_best = history[0]
            for i in range(1, len(history)):
                if history[i] < prev_best:
                    change_x.append(i)
                    change_y.append(history[i])
                    prev_best = history[i]  # Update best-so-far
        
        if change_x:
            ax.scatter(change_x, change_y, s=25, color="#d62728", zorder=3, label="Improvement")

        ax.set_title(title)
        ax.set_xlabel("Epoch")
        ax.set_ylabel(y_label)
        
        # Format Y axis to show plain numbers (no scientific notation)
        try:
            ax.ticklabel_format(style='plain', axis='y', useOffset=False)
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        except Exception:
            pass  # Ignore if formatter fails

        ax.grid(True, alpha=0.3)
        if len(history) > 1:  # Only show legend if we have meaningful data
            ax.legend(loc="best")
        fig.tight_layout()
        return fig