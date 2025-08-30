from abc import ABC, abstractmethod
import scheduler.Common as Common
import csv
import numpy as np
from enum import Enum
import json, os

class Lang(Enum):
    PL = 0
    EN = 1

class BaseMethod(ABC):

    _DESCRIPTIONS_CACHE = None

    def __init__(self, iterations = 100, show_chart=True):
        self.features = Common.read_security_features()
        self.machines = Common.read_machines(self.features)
        self.tasks = Common.read_tasks(self.features)
        self.etc = Common.generate_etc_matrix(self.machines, self.tasks)
        self.iterations = iterations
        self.show_chart = show_chart

    @abstractmethod
    def get_method_name(self):
        """Zwraca nazwę metody."""
        ...

    def get_method_description(self, lang: Lang):
        """
        Wspólne pobieranie opisu z pliku data/descriptions.json na podstawie nazwy metody.
        :param lang: Lang.PL / Lang.EN
        :return: opis (str) lub placeholder gdy brak
        """
        if BaseMethod._DESCRIPTIONS_CACHE is None:
            # plik w katalogu root/data; bieżący plik = scheduler/methods/BaseMethod.py
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            path = os.path.join(base_dir, "data", "descriptions.json")
            with open(path, "r", encoding="utf-8") as f:
                BaseMethod._DESCRIPTIONS_CACHE = json.load(f)

        key = self.get_method_name()

        block = BaseMethod._DESCRIPTIONS_CACHE.get(key, {})
        txt = block.get("pl" if lang == Lang.PL else "en", "").strip()
        return txt if txt else f"(No description for method '{self.get_method_name()}' and lang {lang.name})"

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def optimize(self):
        pass

    @abstractmethod
    def get_best_solution(self):
        pass

    @abstractmethod
    def build_schedule_map(self, solution):
        """Konwersja solution -> {machine_id: [task_ids]}."""
        ...

    def run(self):
        self.initialize()
        self.optimize()
        solution = self.get_best_solution()
        schedule_map = self.build_schedule_map(solution)
        makespan, total_energy = self._compute_metrics(schedule_map)
        Common.print_schedule(schedule_map, self.etc, self.machines, makespan, total_energy)
        if self.show_chart:
            Common.plot_gantt_chart(schedule_map, self.etc, makespan)
        self.write_results_csv(schedule_map, makespan, total_energy)
        return makespan, total_energy
    
    def _compute_metrics(self, schedule_map):
        machine_times = [0.0] * len(self.machines)
        for m_id, tasks in schedule_map.items():
            for t in tasks:
                machine_times[m_id] += self.etc[t][m_id]
        makespan = max(machine_times) if machine_times else 0.0
        total_energy = 0.0
        for m_id, busy in enumerate(machine_times):
            busy_e = busy * self.machines.loc[m_id, 'P_busy']
            idle_e = (makespan - busy) * self.machines.loc[m_id, 'P_idle']
            total_energy += busy_e + idle_e
        return makespan, total_energy

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

    def write_results_csv(self, schedule_map, makespan, total_energy):
            method = self.get_method_name()
            path = f"results/output_{method}.csv"
            # Ustalenie wartości primary / secondary zgodnie z trybem optymalizacji
            if Common.scheduling_mode == Common.MAKESPAN_MODE:
                primary_label = Common.scheduling_modes[Common.MAKESPAN_MODE] + " optimized"
                primary_value = makespan
            else:
                primary_label = Common.scheduling_modes[Common.ENERGY_MODE] + " optimized"
                primary_value = total_energy
            # Wyznacz max liczby zadań (dla kolumn)
            max_tasks = 0
            for tasks in schedule_map.values():
                if tasks:
                    max_tasks = max(max_tasks, len(tasks))
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