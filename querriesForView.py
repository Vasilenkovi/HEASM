import json
from getpass import getpass
from mysql.connector import connect, Error


class ViewSelector:
    def __init__(self):
        columns = "PRODUCT PRODUCT_ID DOI A_PARAMETER_MAX A_PARAMETER_MIN MIXING_METHOD SOURCE_MIX_TIME_MIN SOURCE_MIX_TIME_MAX METHOD GAS SYNTHESIS_TIME_MIN SYNTHESIS_TIME_MAX FEATURE CONTRIBUTOR COMMENTS synthesis_parameters synthesis_units synthesis_min_values synthesis_max_values meas_parameters meas_units meas_mins meas_maxes All_ingredients words countries internal_cipher url YEAR journal impact"
        self.allColumns = columns.split()
        self.allComments = {
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
            "synthesis_units": "Единицы измерения",
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

        self.convolvedColumnComments = ["Формула продукта", "Идентификатор продукта внутри базы", "DOI",
                                        "Значение параметра А кубической фазы", "Метод смешивания",
                                        "Значение времени смешивания сырья, часы",
                                        "Метод синтеза/или метод проведения теоретических исследований", "Защитный газ",
                                        "Значение времени синтеза, минуты", "Признак работы", "ФИО вписавшего",
                                        "Комментарии", "Параметры синтеза", "Параметры измерений",
                                        "Список ингредиентов", "Ключевые слова", "Страны публикации", "Внутренний шифр",
                                        "Ссылка", "Год выхода", "Журнал", "Импакт фактор"]

    def selectInfo(self, listOfColumns):  # querry to get all columns in list
        if (len(listOfColumns) == 0):
            listOfColumns = self.allColumns
        querry = "SELECT "
        for i in listOfColumns:
            querry += i + ', '
        querry = querry[0: len(querry) - 2] + " FROM main_view;"
        return querry

    def querryTableInfo(self):  # querry to get general info about table
        querry = "SHOW COLUMNS FROM MAIN_VIEW;"
        return querry

    def querryForComments(self):  # querry to get comments to the table
        return "SELECT table_comment     FROM INFORMATION_SCHEMA.TABLES     WHERE table_schema=\'heasm\'         AND table_name=\'main_view\';"

    def getAllColumns(self):  # get list of all collumns
        return self.allColumns

    def convertCells(self, lst):
        # print(lst)
        length = len(lst)
        first = 'None'
        second = 'None'

        if (lst[length - 1].replace('.', '').replace(' ', '').replace('-', '').isdigit()):
            second = float(lst[length - 1])
            # print(second)
        if (lst[length - 2].replace('.', '').replace(' ', '').replace('-', '').isdigit()):
            first = float(lst[length - 2])
            # print(first)
        if (first == 'None' and second == 'None'):
            lst[length - 2] = ""
        elif (first == 'None' and second != 'None'):
            lst[length - 2] = str(second)
        elif (first != 'None' and second == 'None'):
            lst[length - 2] = str(first)
        elif (first != 'None' and second != 'None' and first == second):
            lst[length - 2] = str(first)
        elif (first != 'None' and second != 'None'):
            lst[length - 2] = "[" + str(min(second, first)) + "," + str(max(second, first)) + "]"
        lst.pop(length - 1)
        # print(lst)
        return lst

    def convertConcat(self, matrix,
                      lstToConcat):  # unites columns and converts resulting cells into json WARNING: returns array of arrays
        matrix = [list(i) for i in matrix]
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                matrix[i][j] = str(matrix[i][j])
        for i in lstToConcat:
            for j in range(len(matrix)):
                tmpLst = []
                tempStr = ""
                lstToSub = []
                for k in i:
                    tmp = matrix[j][k]
                    tmp = tmp.split(';')
                    lstToSub.append(tmp)
                for k in range(len(lstToSub[0])):
                    for h in lstToSub:
                        # print(h,"||" ,lstToSub, k)
                        try:
                            if h[k] != "None":
                                tempStr += h[k] + "|"
                            else:
                                tempStr += "None" + "|"
                        except:
                            tempStr += "None" + "|"
                    tempStr = tempStr.split('|')
                    tempStr = [u for u in tempStr if u != ""]
                    tmpLst.append(list(tempStr))
                    tempStr = ""
                # print(tmpLst)
                result = [self.convertCells(tmpLst[t]) for t in range(len(tmpLst))]
                if len(result)==1 and len(result[0])==1:
                    result = result[0][0]
                matrix[j][i[0]] = result
        for i in range(len(lstToConcat)):
            for j in range(len(lstToConcat[i]) - 1, 0, -1):
                for k in range(len(matrix)):
                    x = matrix[k].pop(lstToConcat[i][j])
        return matrix

    def concatIngWord(self, matrix,
                      lst):  # converts cells with multiple values to json WARNING: returns array of arrays
        matrix = [list(i) for i in matrix]
        for i in lst:
            for k in range(len(matrix)):
                tmpLst = matrix[k][i].split(';')
                matrix[k][i] = [[k] for k in tmpLst]
        return matrix

    # Combines all semantically dependent columns and aggregates multiple-valued entries to JSON strings, while handling column comments shifting
    # Parameters: listOfTuples - MySQL returned list of tuples of raw view
    # Returns: tuple (newTable, listOfComments, listMask):
    #         newTable - table with concatenated columns and JSON serialized lists
    #         listOfComments - list with comments to each column in newTable
    def convolvedColumnsView(self, listOfTuples: list[tuple]) -> (list[list], list):
        matrix = self.convertConcat(listOfTuples, [[19, 20, 21, 22], [15, 16, 17, 18], [10, 11], [6, 7], [3, 4]])
        matrix = self.concatIngWord(matrix, [15, 14])

        return matrix, self.convolvedColumnComments



