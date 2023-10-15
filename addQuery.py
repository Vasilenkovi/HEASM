class AddQuery:
    WEB_VIEW_BASE_INFO = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 20, 21]
    WEB_VIEW_COMPOSITES = [["Параметры синтеза:", ["Параметр", "Еденица измерения", "Значение"]], ["Параметры измерений:", ["Параметр", "Еденица измерения", "Значение"]], ["Ингредиенты:", ["Ингредиент"]], ["Ключевые слова:", ["Ключевое слово"]], ["Страны публикации:", ["Страна"]]]

    def getAddCols(self) -> tuple[list, list[list]]:
        return AddQuery.WEB_VIEW_BASE_INFO, AddQuery.WEB_VIEW_COMPOSITES