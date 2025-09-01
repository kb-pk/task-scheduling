from lang.Translations import Translations

from scheduler.ProgramState import ProgramState

class T:
    """
    A very crude translator class.
    """

    def __init__(self, state: ProgramState):
        self.__state = state

        self.__t_file = Translations(self.__state).translation

    def t(self, string: str):
        """
        Wraps around a strings and returns a current-lang equivalent
        """
        return self.__t_file.get(string, string)

    def tl(self, strings: list[str]):
        """
        Same as t(), but wraps around a list of strings

        :return: A list of translated strings
        """
        translations = []
        for s in strings:
            translations.append(self.t(s))

        return translations

    def td(self, translations: dict):
        """
        Wraps around a dictionary the like of {LangState.State.*: "literal in that language", ...}
        Useful for strings too long to be added to the .ini file.

        :return: A string corresponding to that language
        """
        current_lang = self.__state.lang.get()

        return translations[current_lang]