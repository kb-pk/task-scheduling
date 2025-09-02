import os


def prepare_results_directory():
    """
    Prepare the results directory for storing output files and clean up old results.
    """
    results_dir = "results"
    os.makedirs("results", exist_ok=True)
    
     # Iterate over all the files in the directory and remove them
    for filename in os.listdir(results_dir):
        file_path = os.path.join(results_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def are_security_features_correct(item, features):
    """
    Sprawdzenie czy cechy bezpieczeństwa na maszynie lub w zadaniu są mniejsze niż definicja
    :param item: wiersz z macierzy maszyn lub zadań
    :param features: macierz cech
    :return: False jeśli dowolna cecha maszyny lub zadania jest większa niż definicja, True w przeciwnym wypadku
    """

    for feature_id in features.index.values:
        feature_name = features.values[feature_id][0]
        feature_value = features.values[feature_id][1]
        if item[feature_name] > feature_value:
            return False

    return True


def can_execute_task_on_machine(machine, task, features):
    """
    Sprawdzenie czy można wykonać zadanie na maszynie,
    czyli czy wszystkie wartości cech wymaganych przez zadanie są mniejsze niż cechy maszyny
    :param machine: wiersz określający maszynę
    :param task: wiersz określający zadaine
    :param features: macierz cech bezpieczenstwa
    :return: True jesli można wykonać zadanie, False w przeciwnym wypadku
    """
    for feature_id in features.index.values:
        feature_name = features.values[feature_id][0]
        if task[feature_name] > machine[feature_name]:
            return False

    return True
