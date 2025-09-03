import numpy as np

from scheduler.methods.EvolAlgoBaseMethod import EvolAlgoBaseMethod


class ParticleSwarmMethod(EvolAlgoBaseMethod):
    def build_schedule_map(self, solution):
        assign = np.rint(solution).astype(int)
        np.clip(assign, 0, len(self.machines) - 1)

        schedule_map = {m_id: [] for m_id in range(len(self.machines))}

        for t_id, m_id in enumerate(assign):
            schedule_map[m_id].append(t_id)

        return schedule_map

    def _generate_population(self):
        self.population = np.random.uniform(0, len(self.machines) - 1,
                                            size=(self._pop_size.get_value(), len(self.tasks)))
        self._velocity = np.zeros_like(self.population)

    def _crossover_population(self):
        pass

    def _mutate_population(self):
        pass

    def optimize(self):
        self._record_history_point()
