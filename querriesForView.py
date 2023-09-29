import json
from getpass import getpass
from mysql.connector import connect, Error
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
        self.transformedColumnComments = ["Формула продукта", "Идентификатор продукта внутри базы", "DOI", "Pначение параметра А кубической фазы", "Метод смешивания", "Pначение времени смешивания сырья, часы", "Метод синтеза/или метод проведения теоретических исследований", "Защитный газ", "Значение времени синтеза, минуты", "Признак работы", "ФИО вписавшего", "Комментарии", "Параметры синтеза", "Параметры измерений", "Список ингредиентов", "Ключевые слова", "Страны публикации", "Внутренний шифр", "Ссылка", "Год выхода", "Журнал", "Импакт фактор"]

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

    #Turns couples of min, max columns to single range column. If values are a range, "[a, b]" string format is provided. If a == b, a single value is recorded
    #Parameters: matrix - MySQL returned table
    #            listOfPairs - list of tuples (a, b) where 'a' is a column index of min value and 'b' is a column index of max value 
    #            multipleSeparator - string separator for multiple-valued columns
    def rangify(matrix: list[tuple], listOfPairs: list[tuple], multipleSeparator: str) -> list[list]:
        out = []
        listOfPairs.sort(key = lambda x: min(x), reverse=True)

        for row in matrix:
            rowList = list(row)

            for a, b in listOfPairs:
                aValList = rowList[a]
                bValList = rowList[b]

                if None in (aValList, bValList):
                    if aValList == None:
                        rowList[a] = bValList
                        rowList.pop(b)
                    continue

                aValList = str(aValList).split(multipleSeparator)
                bValList = str(bValList).split(multipleSeparator)

                aLen = len(aValList)
                bLen = len(bValList)

                if aLen != bLen:
                    maxLen = max(aLen, bLen)
                    aValList = aValList + [None] * (maxLen - aLen)
                    bValList = bValList + [None] * (maxLen - bLen)
                
                if len(aValList) < 2:
                    aVal = rowList[a]
                    bVal = rowList[b]

                    if aVal != bVal:
                        rowList[a] = "[{a}, {b}]".format(a=aVal, b=bVal)
                    rowList.pop(b)

                else:
                    concatList = []


                    for aVal, bVal in zip(aValList, bValList):

                        if None in (aVal, bVal):
                            if aVal == None:
                                concatList.append(bVal)
                        elif aVal != bVal:
                            concatList.append("[{a}, {b}]".format(a=aVal, b=bVal))
                        else:
                            concatList.append(aVal)

                    rowList[a] = "; ".join(concatList)
                    rowList.pop(b)

            out.append(rowList)

        return out

    def convertConcat(matrix, lstToConcat): # unites columns and converts resulting cells into json WARNING: returns array of arrays
        matrix = [list(i) for i in matrix]
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                matrix[i][j] = str(matrix[i][j])
        for i in lstToConcat:
            for j in range(len(matrix)):
                tempStr = ""
                lstToSub = []
                for k in i:
                    tmp = matrix[j][k]
                    tmp = tmp.split(';')
                    lstToSub.append(tmp)
                for k in range(len(lstToSub[0])):
                    for h in lstToSub:
                        #print(h,"||" ,lstToSub, k)
                        #try:
                            tempStr += h[k]+" "
                        #except:
                        #    pass #Catch exceptions here
                    tempStr += ";"
                result = dict()
                tempStr = tempStr.split(";")
                for t in range(len(tempStr)):
                    result[t]=tempStr[t]
                matrix[j][i[0]] = json.dumps(result)
        for i in range(len(lstToConcat)):
            for j in range(len(lstToConcat[i])-1,0,-1):
                for k in range(len(matrix)):
                    x = matrix[k].pop(lstToConcat[i][j])
        return matrix
    
    def convertToJson(matrix, lst): # converts cells with multiple values to json WARNING: returns array of arrays
        matrix = [list(i) for i in matrix]
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                matrix[i][j] = str(matrix[i][j])
        for i in lst:
            for k in range(len(matrix)):
                strTmp =  matrix[k][i]
                strTmp = strTmp.split(';')
                tmpDict = dict()
                for j in range(len(strTmp)):
                    tmpDict[j] = strTmp[j]
                matrix[k][i] = json.dumps(tmpDict)
        return matrix

    #Example
    # try:
    #     with connect(
    #         host="localhost",
    #         user="root",
    #         password="Sciilotv2003!",
    #     ) as connection:
    #         show_db_query = "use heasm;"
    #         cursor = connection.cursor()
    #         cursor.execute(show_db_query)
    #         cursor.execute("select * from main_view;")
    #         matrix = cursor.fetchall()
    #         matrix = convertConcat(matrix, [[15,16,17,18],[3,4]])
    """       
              The second parameter of this function 
              is an array of arrays, where within each there are columns to be combined. 
              Moreover, the elements of the left array must be greater than the values of the right arrays. 
              Also, each array must be sorted in ascending order.
    """
    #         #print(matrix)
    #         print(matrix[0][19])
    #         print()
    #         print(convertToJson(matrix, [19])[0][19])
    """
              The second parameter of this function is an array with indexes of column with multiple values.
              The order of the values is not important. Take into account that convertConcat deletes odd columns
              For example after previous function call columns 18, 17, 16, 4 had been removed. But I recommend you use this 
              function before convertConcat.
    """
    # except Error as e:
    #     print(e)


    #Combines all semantically dependent columns and aggregates multiple-valued entries to JSON strings, while handling column comments shifting
    #Parameters: listOfTuples - MySQL returned list of tuples of raw view
    #Returns: tuple (newTable, listOfComments):
    #         newTable - table with concatenated columns and JSON serialized lists
    #         listOfComments - list with comments to each column in newTable
    def convolvedColumnsView(self, listOfTuples: list[tuple]) -> tuple[list[list], list]:
        t = ViewSelector.rangify(listOfTuples, [(21, 22), (17, 18), (10, 11), (6, 7), (4, 3)], "; ") #What a hecking order
        #newTable = ViewSelector.convertConcat(listOfTuples, [[15, 16, 17, 18], [19, 20, 21, 22], [10, 11], [6, 7] , [3, 4]])
        #newTable = ViewSelector.convertToJson(newTable, [19]) #TODO
        
        #TODO listOfComments

        return t

