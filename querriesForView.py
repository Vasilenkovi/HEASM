class ViewSelector:
    def __init__(self):
        columns = "PRODUCT PRODUCT_ID DOI A_PARAMETER_MAX A_PARAMETER_MIN MIXING_METHOD SOURCE_MIX_TIME_MIN SOURCE_MIX_TIME_MAX METHOD GAS SYNTHESIS_TIME_MIN SYNTHESIS_TIME_MAX FEATURE CONTRIBUTOR COMMENTS synthesis_parameters synthesis_units synthesis_min_values synthesis_max_values meas_parameters meas_units meas_mins meas_maxes All_ingredients words countries internal_cipher url YEAR journal impact"
        self.allColumns = columns.split()
        self.allComments =  {
"PRODUCT": "Формула продукта",
"PRODUCT_ID": "Идентификатор продукта внутри базы",
"DOI": "DOI",
"A_PARAMETER_MAX": "Минимальное значение параметра А кубической фазы",
"A_PARAMETER_MIN": "Максимальное значение параметра А кубической фазы",
"MIXING_METHOD": "Метод смешивания",
"SOURCE_MIX_TIME_MIN": "Минимальное значение времени смешивания сырья, часы",
"SOURCE_MIX_TIME_MAX": "Максимальное значение времени смешивания сырья, часы",
"METHOD": "Метод смешивания",
"GAS": "Защитный газ",
"SYNTHESIS_TIME_MIN": "Минимальное значение времени синтеза, минуты",
"SYNTHESIS_TIME_MAX": "Максимальное значение времени синтеза, минуты",
"FEATURE": "Признак работы",
"CONTRIBUTOR": "ФИО вписавшего",
"COMMENTS": "Комментарии",
"synthesis_parameters": "Параметры синтеза",
"synthesis_units": "Единицы измерения" ,
"synthesis_min_values": "Минимальные значения параметров синтеза",
"synthesis_max_values": "Максимальные значения параметров синтеза",
"meas_parameters": "Параметры измерений",
"meas_units": "Единицы измерений замеряемых параметров",
"meas_mins": "Минимальные значения замеряемых параметров",
"meas_maxes": "Максимальные значения замеряемых параметров",
"All_ingredients": "Список ингредиентов",
"words": "Ключевые слова",
"countries": "Страны публикации",
"internal_cipher": "Внутренний шифр",
"url": "Ссылка",
"YEAR": "Год выхода",
"journal": "Журнал",
"impact": "Импакт фактор"
}
    def selectInfo(self, listOfColumns): # querry to get all columns in list
        if(len(listOfColumns)==0):
            listOfColumns = self.allColumns
        querry = "SELECT "
        for i in listOfColumns:
            querry += i + ', '
        querry = querry[0: len(querry)-2] + " FROM MAIN_VIEW;"
        return querry
    def querryTableInfo(self): # querry to get general info about table
        querry = "SHOW COLUMNS FROM MAIN_VIEW;"
        return querry
    def querryForComments(self): # querry to get comments to the table
        return "SELECT table_comment     FROM INFORMATION_SCHEMA.TABLES     WHERE table_schema=\'heasm\'         AND table_name=\'MAIN_VIEW\';"
    def getAllColumns(self): # get list of all collumns
        return self.allColumns

