from datetime import date
from typing import List

URL = "https://kino-format.ru/cinemas/kinotsentr-kf-balashikha/"


def fetch_kinoformat_titles(day: date) -> List[str]:
    # На текущий момент расписания нет. Вернём пустой список.
    return []
