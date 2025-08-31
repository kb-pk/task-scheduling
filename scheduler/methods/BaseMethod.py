from abc import ABC, abstractmethod
import scheduler.Common as Common
import csv
import numpy as np
from enum import Enum
import yaml, os
from tabulate import tabulate
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.patches import Patch

class Lang(Enum):
    PL = 0
    EN = 1

class BaseMethod(ABC):

    _DESCRIPTIONS_CACHE = None
    _singleton_instance = None

    def __init__(self, iterations = 100, show_chart=True):
        self.features = Common.read_security_features()
        self.machines = Common.read_machines(self.features)
        self.tasks = Common.read_tasks(self.features)
        self.etc = Common.generate_etc_matrix(self.machines, self.tasks)
        self.iterations = iterations
        self.show_chart = show_chart
        # Cached last run artifacts (for GUI one‑click access)
        self.last_schedule_map = None
        self.last_makespan = None
        self.last_total_energy = None
        self.last_solution = None

    @abstractmethod
    def set_parameters(self, **kwargs):
        """
        Update ALL algorithm parameters (mirror of __init__ args except self).
        Must be implemented in each subclass; should NOT recreate heavy data,
        only assign fields and recompute derived ones if needed.
        """
        raise NotImplementedError

    @abstractmethod
    def get_method_name(self):
        """Zwraca nazwę metody."""
        raise NotImplementedError

    def get_method_description(self, lang: Lang):
        """
        Return method description loaded from data/descriptions.yaml (YAML only).
        YAML structure:
          method_key:
            pl: |-
              ...
            en: |-
              ...
        If key or language text is missing – returns placeholder.
        """
        if BaseMethod._DESCRIPTIONS_CACHE is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            yaml_path = os.path.join(base_dir, "data", "descriptions.yaml")
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    BaseMethod._DESCRIPTIONS_CACHE = yaml.safe_load(f) or {}
            except FileNotFoundError:
                BaseMethod._DESCRIPTIONS_CACHE = {}
            except Exception as e:
                print(f"[WARN] Failed to load YAML descriptions: {e}")
                BaseMethod._DESCRIPTIONS_CACHE = {}
        key = self.get_method_name()
        block = BaseMethod._DESCRIPTIONS_CACHE.get(key, {}) if isinstance(BaseMethod._DESCRIPTIONS_CACHE, dict) else {}
        txt = block.get("pl" if lang == Lang.PL else "en", "")
        txt = (txt or "").strip()
        return txt if txt else f"(No YAML description for '{key}' / {lang.name})"

    @abstractmethod
    def initialize(self):
        raise NotImplementedError

    @abstractmethod
    def optimize(self):
        raise NotImplementedError

    @abstractmethod
    def get_best_solution(self):
        raise NotImplementedError

    @abstractmethod
    def build_schedule_map(self, solution):
        """Konwersja solution -> {machine_id: [task_ids]}."""
        raise NotImplementedError

    def run(self):
        self.initialize()
        self.optimize()
        solution = self.get_best_solution()
        schedule_map = self.build_schedule_map(solution)
        makespan, total_energy = self._compute_metrics(schedule_map)

        # cache results
        self.last_solution = solution
        self.last_schedule_map = schedule_map
        self.last_makespan = makespan
        self.last_total_energy = total_energy
    
    def _makespan(self, schedule_map, machine_times):
        machine_times = [0.0] * len(self.machines)
        for m_id, tasks in schedule_map.items():
            for t in tasks:
                machine_times[m_id] += self.etc[t][m_id]
        makespan = max(machine_times) if machine_times else 0.0
        return makespan

    def _energy(self, makespan, machine_times):
        total_energy = 0.0
        for m_id, busy in enumerate(machine_times):
            busy_e = busy * self.machines.loc[m_id, 'P_busy']
            idle_e = (makespan - busy) * self.machines.loc[m_id, 'P_idle']
            total_energy += busy_e + idle_e
        return total_energy

    def _compute_metrics(self, schedule_map):
        machine_times = [0.0] * len(self.machines)
        makespan = self._makespan(schedule_map, machine_times)
        energy = self._energy(makespan, machine_times)
        return makespan, energy

    def _format_task_cell(self, task_id: int, machine_id: int) -> str:
        """
        Format pojedynczej komórki z zadaniem w CSV (i potencjalnie innych wyjściach).
        Można nadpisać w klasie potomnej aby zmienić sposób prezentacji.
        Domyślnie:
          - tryb makespan:    "<id> (czas)"
          - tryb energy:      "<id> (energia)"
          - tryb all:         "<id> (czas|energia)"
        """
        duration = self.etc[task_id][machine_id]
        energy = duration * self.machines.loc[machine_id, 'P_busy']
        if Common.output_mode == Common.MAKESPAN_O_MODE:
            return f"{task_id} ({duration:.1f})"
        if Common.output_mode == Common.ENERGY_O_MODE:
            return f"{task_id} ({energy:.1f})"
        if Common.output_mode == Common.ALL_O_MODE:
            return f"{task_id} ({duration:.1f}|{energy:.1f})"
        return str(task_id)

    def write_results_csv(self):
        if self.last_schedule_map is None or self.last_makespan is None or self.last_total_energy is None:
            print("[WARN] No cached run data to write CSV (run method first).")
            return
        schedule_map = self.last_schedule_map
        makespan = self.last_makespan
        total_energy = self.last_total_energy

        method = self.get_method_name()
        path = f"results/output_{method}.csv"

        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            primary_label = Common.scheduling_modes[Common.MAKESPAN_MODE] + " optimized"
            primary_value = makespan
        else:
            primary_label = Common.scheduling_modes[Common.ENERGY_MODE] + " optimized"
            primary_value = total_energy

        max_tasks = max((len(t) for t in schedule_map.values()), default=0)
        header = ["Machine/Tasks"] + [str(i) for i in range(max_tasks)]
        if Common.output_mode in (Common.ENERGY_O_MODE, Common.ALL_O_MODE):
            header.append("IDLE")

        with open(path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow([primary_label, f"{primary_value:.4f}".replace('.', ',')])
            writer.writerow(header)
            for m_id in sorted(schedule_map.keys()):
                tasks = schedule_map[m_id]
                row = [m_id]
                time_sum = 0.0
                for task_id in tasks:
                    row.append(self._format_task_cell(task_id, m_id))
                    time_sum += self.etc[task_id][m_id]
                if len(tasks) < max_tasks:
                    row.extend([''] * (max_tasks - len(tasks)))
                if Common.output_mode in (Common.ENERGY_O_MODE, Common.ALL_O_MODE):
                    idle_time = makespan - time_sum
                    idle_energy = idle_time * self.machines.loc[m_id, 'P_idle']
                    row.append(f"{idle_time:.1f}|{idle_energy:.1f}")
                writer.writerow(row)

    def print_schedule(self):
        if self.last_schedule_map is None:
            print("[WARN] No schedule to print (run method first).")
            return
        schedule_map = self.last_schedule_map
        makespan = self.last_makespan
        total_energy = self.last_total_energy

        print("\n" + "=" * 50)
        print(f"Method: {self.get_method_name()}")
        if Common.output_mode in [Common.MAKESPAN_O_MODE, Common.ALL_O_MODE]:
            print(f"Makespan: {makespan:.2f}")
        if Common.output_mode in [Common.ENERGY_O_MODE, Common.ALL_O_MODE]:
            print(f"Total energy: {total_energy:.2f}")
        print("=" * 50 + "\n")

        for machine_id in sorted(schedule_map.keys()):
            tasks = schedule_map[machine_id]
            if not tasks:
                continue
            machine_time = sum(self.etc[t][machine_id] for t in tasks)
            busy_energy = machine_time * self.machines.loc[machine_id, 'P_busy']
            idle_energy = (makespan - machine_time) * self.machines.loc[machine_id, 'P_idle']
            total_e = busy_energy + idle_energy
            print(f"Machine {machine_id}")
            if Common.output_mode in [Common.MAKESPAN_O_MODE, Common.ALL_O_MODE]:
                print(f"  Busy time: {machine_time:.2f}")
            if Common.output_mode in [Common.ENERGY_O_MODE, Common.ALL_O_MODE]:
                print(f"  Energy: {total_e:.2f} (busy {busy_energy:.2f}, idle {idle_energy:.2f})")
            print("  Tasks:")
            for t in tasks:
                d = self.etc[t][machine_id]
                e = d * self.machines.loc[machine_id, 'P_busy']
                if Common.output_mode == Common.MAKESPAN_O_MODE:
                    print(f"    - Task {t} (time {d:.2f})")
                elif Common.output_mode == Common.ENERGY_O_MODE:
                    print(f"    - Task {t} (energy {e:.2f})")
                else:
                    print(f"    - Task {t} (time {d:.2f}, energy {e:.2f})")
            print("-" * 30)

    def plot_gantt_chart(self):
        if self.last_schedule_map is None or self.last_makespan is None:
            print("[WARN] No schedule to plot (run method first).")
            return
        schedule_map = self.last_schedule_map
        makespan = self.last_makespan

        MAX_WIDTH_INCHES = 100
        fig_width = min(max(15, makespan / 10 if makespan else 15), MAX_WIDTH_INCHES)
        fig_height = max(6, len(schedule_map) * 0.5)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        num_tasks = len(self.etc)
        colors = cm.viridis(np.linspace(0, 1, num_tasks))

        for machine_id in sorted(schedule_map.keys()):
            current_time = 0.0
            for task_id in schedule_map[machine_id]:
                duration = self.etc[task_id][machine_id]
                ax.barh(machine_id, duration,
                        left=current_time,
                        height=0.6,
                        align='center',
                        color=colors[task_id],
                        edgecolor='black')
                current_time += duration

        ax.set_yticks(sorted(schedule_map.keys()))
        ax.set_yticklabels([f"Machine {m}" for m in sorted(schedule_map.keys())])
        ax.invert_yaxis()
        ax.set_xlabel('Time')
        ax.set_title(f'Schedule (Gantt) - {self.get_method_name()}')
        ax.grid(True, linestyle='--', linewidth=0.5)
        ax.axvline(makespan, color='red', linestyle='--', linewidth=1.2)
        ax.text(makespan, 0.5, f'Makespan: {makespan:.2f}',
                rotation=90, va='bottom', ha='left',
                color='red', fontsize=9, backgroundcolor='white')

        plt.tight_layout()
        out_path = f"results/gantt_{self.get_method_name()}.png"
        plt.savefig(out_path)
        print(f"Saved Gantt chart to: {out_path}")
        plt.show()