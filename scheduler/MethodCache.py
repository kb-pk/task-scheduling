from enum import Enum

import numpy as np
import pandas as pd

from scheduler import Common


class MethodCache:
    """
    To avoid having to read/generate immutable stuff stored in the base method every instantiation
    """
    class CacheObject(Enum):
        security_features = 0
        machines = 1
        tasks = 2
        etc_matrix = 3

    def __init__(self):
        self.__cache = {}

        self.method_to_object = {
            self.CacheObject.security_features: self.__read_security_features,
            self.CacheObject.machines: self.__read_machines,
            self.CacheObject.tasks: self.__read_tasks,
            self.CacheObject.etc_matrix: self.__generate_etc_matrix
        }

    def __getitem__(self, key: CacheObject):
        if not self.__cache.__contains__(key):
            self.__cache[key] = self.method_to_object[key]()

        return self.__cache[key]

    def __are_security_features_correct(self, item):
        """
        Sprawdzenie czy cechy bezpieczeństwa na maszynie lub w zadaniu są mniejsze niż definicja
        :param item: wiersz z macierzy maszyn lub zadań
        :param features: macierz cech
        :return: False jeśli dowolna cecha maszyny lub zadania jest większa niż definicja, True w przeciwnym wypadku
        """
        features = self[self.CacheObject.security_features]

        for feature_id in features.index.values:
            feature_name = features.values[feature_id][0]
            feature_value = features.values[feature_id][1]
            if item[feature_name] > feature_value:
                return False

        return True

    def __read_security_features(self):
        """
        Wczytanie listy cech bezpieczeństwa i ich wag, lista cech może być dowolnie długa

        :return: macierz cecha-waga
        """
        security_features_filename = "data/security_features_list.csv"
        skip_rows = [0]
        column_delimiter = ';'
        column_names = ['security_feature', 'weight']
        feature_matrix = pd.read_csv(security_features_filename, skiprows=skip_rows, delimiter=column_delimiter,
                                     index_col=False, names=column_names)

        return feature_matrix

    def __read_machines(self):
        """
        Wczytanie macierzy maszyn z pliku CSV

        :return: macierz maszyn
        """
        features = self[self.CacheObject.security_features]

        machines_filename = "data/M20_security_features.csv"
        skip_rows = [0, 1]
        column_delimiter = ';'
        column_names = ['CC', 'cores', 'P_busy', 'P_idle', 'A', 'B', 'C', 'D', 'E']
        machines = pd.read_csv(machines_filename, skiprows=skip_rows, delimiter=column_delimiter, index_col=False,
                               names=column_names)

        for machine_id in machines.index.values:
            if not self.__are_security_features_correct(machines.iloc[machine_id]):
                raise Exception(
                    "Machine features greater than defined. Machine:\n" + machines.iloc[machine_id].to_string())

        return machines

    def __read_tasks(self):
        """
        Wczytanie macirzy zadań z pliku CSV

        :return: macierz zadań
        """
        features = self[self.CacheObject.security_features]

        tasks_filename = "data/T200_security_features.csv"
        skip_rows = [0, 1]
        column_delimiter = ';'
        column_names = ['WL_seq', 'WL_par', 'A', 'B', 'C', 'D', 'E']
        tasks = pd.read_csv(tasks_filename, skiprows=skip_rows, delimiter=column_delimiter, index_col=False,
                            names=column_names)
        for task_id in tasks.index.values:
            if not self.__are_security_features_correct(tasks.iloc[task_id]):
                raise Exception(
                    "Task features requirements greater than defined. Task:\n" + tasks.iloc[task_id].to_string())

        return tasks

    def __generate_etc_matrix(self):
        """
        Generowanie mcierzy ETC z uwzględnieniem przetwarzania równoległego i sekwencyjnego
        Macierz ETC - macierz spodziewanego czasu wykonania zadania na maszynie

        ETC[i][j] = wls/cc + wlp/(cn * cc)
            wls - liczba operacji zmiennoprzecinkowych które NIE MOGĄ zostać zrównoleglone
            wlp - liczba operacji zmiennoprzecinkowych które MOGĄ zostać zrównoleglone
            cc - zdolność obliczeniowa jednego rdzenia
            cn - liczba rdzeni

        :return: macierz ETC
        """
        machines = self[self.CacheObject.machines]
        tasks = self[self.CacheObject.tasks]

        new_etc = np.zeros(shape=(len(tasks), len(machines)), dtype=np.float64)  # utworzenie pustej tablicy

        for task_id in tasks.index.values:  # iteracja po wszystkich zadaniach
            wls = tasks.values[task_id][0]  # liczba operacji których NIE MOŻNA zrównoleglić
            wlp = tasks.values[task_id][1]  # liczba operacji które MOŻNA zrówloleglić
            for machine_id in machines.index.values:  # literacje po wszystkich maszynach
                cc = machines.values[machine_id][0]  # zdolność obliczenniowa maszyny
                cn = machines.values[machine_id][1]  # liczba rdzeni maszyny
                # obliczenie spodziewanego czasu wykonania zadania na maszynie
                new_etc[int(task_id)][int(machine_id)] = wls / cc + wlp / (cn * cc)

        return new_etc
