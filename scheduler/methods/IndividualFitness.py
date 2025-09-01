from scheduler.ProgramState import ProgramState

class IndividualFitness:
    """
    A wrapper class that is marginally better than just addressing the dict by hand
    """
    def __init__(self, state: ProgramState, metrics):
        self.state = state

        self.metrics = metrics

    def scheduling(self):
        return self.metrics[self.state.scheduling.get()]

    def output(self):
        return self.metrics[self.state.output.get()]

    def get_all(self):
        return self.metrics