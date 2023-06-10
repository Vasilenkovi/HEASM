

class QuerryBuilder():

    lookUp = {}
    columnComments = []
    logComments = []
    editSelected = []
    editTables = []
    remaining = []
    dataTypeByComment = {}
    dataTypeByName = {}

    TABLES = {"bib_source": 0, "bibliography": 1, "countries": 2, "ingredients": 3, "key_word": 4, "measurements": 5, "synthesis_parameter": 6, "synthesis_product": 7}
    TABLES_INVERSE = ["bib_source", "bibliography", "countries", "ingredients", "key_word", "measurements", "synthesis_parameter", "synthesis_product"]

    TABLES_ADJACENCY = [
        [None, ['JOURNAL', 'YEAR'], None, None, None, None, None, None],
        [['JOURNAL', 'YEAR'], None, ['DOI'], None, ['DOI'], None, None, ['DOI']],
        [None, ['DOI'], None, None, None, None, None, None],
        [None, None, None, None, None, None, None, ['PRODUCT_ID']],
        [None, ['DOI'], None, None, None, None, None, None],
        [None, None, None, None, None, None, None, ['PRODUCT_ID']],
        [None, None, None, None, None, None, None, ['PRODUCT_ID']],
        [None, ['DOI'], None, ['PRODUCT_ID'], None, ['PRODUCT_ID'], ['PRODUCT_ID'], None]
    ]

    PARENT_TABLES = {"JOURNAL": "bib_source", "DOI": "bibliography", "PRODUCT_ID": "synthesis_product"}
    TABLE_PRIORITY = ["bib_source", "bibliography", "key_word", "countries", "synthesis_product", "ingredients", "measurements", "synthesis_parameter"]

    def __init__(self, in_lookUp: dict, in_columnComments: list, in_logComments: list, in_tablesForTableCols: list, in_tableCols: list, in_dataTypeByComment: dict, in_dataTypeByName: dict) -> None:
        self.lookUp = in_lookUp
        self.columnComments = in_columnComments
        self.logComments = in_logComments
        self.tablesForTableCols = in_tablesForTableCols
        self.tableCols = in_tableCols
        self.dataTypeByComment = in_dataTypeByComment
        self.dataTypeByName = in_dataTypeByName

    def escapeString(string: str) -> str:
        res = r""
        for c in string:
            if c in ('"', "'", ";", "%", "_"):
                res += "\{}".format(c)
            else:
                res += c
        return res

    def __leastTables(self, col1, col2) -> list:
        for i in self.lookUp[col1]:
            for j in self.lookUp[col2]:
                if i == j:
                    return [i]
        #Else BFS
        table1 = self.lookUp[col1][0]
        table2 = self.lookUp[col2][0]
        queue = []
        queue.append(QuerryBuilder.TABLES[table1])
        visited = [False for i in range(8)]
        visited[QuerryBuilder.TABLES[table1]] = True
        prev = [-1 for i in range(8)]

        while len(queue) > 0:
            v = queue[0]
            queue.pop(0)
            for i in range(8):
                if QuerryBuilder.TABLES_ADJACENCY[v][i] != None and not visited[i]:
                    queue.append(i)
                    visited[i] = True
                    prev[i] = v
                    if i == QuerryBuilder.TABLES[table2]:
                        queue.clear()
                        break

        out = []
        current = table2
        out.append(current)
        while current != table1:
            current = QuerryBuilder.TABLES_INVERSE[prev[QuerryBuilder.TABLES[current]]]
            out.append(current)

        return out

    def buildQuerry(self, requestArgs, selected: list) -> str:
        selected_filters = requestArgs.getlist('select_filters')
        where_filters = requestArgs.getlist('where_filters')

        if len(selected_filters) == 0:
            return ""

        querry = "SELECT DISTINCT " #base of querry
        preselect = []
        select = [] #all columns to select
        where = [] #all columns to include in "WHERE" statement
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        sort = 0
        sortCol = ""
        tables = []

        tempSelected = []
        for i in selected:
            if i in selected_filters or i in where_filters:
                tempSelected.append(i)
        selected = tempSelected
        QuerryBuilder.remaining = tempSelected

        for i in selected_filters:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i:
                    preselect.append(self.columnComments[j][0]) 

        if len(preselect) > 1:
            for i1 in range(len(preselect)-1):
                for i2 in range(i1+1, len(preselect)):
                    tables2 = self.__leastTables(preselect[i1], preselect[i2])
                    for t in tables2:
                        if t not in tables:
                            tables.append(t)
        else:
            tables.append(self.lookUp[preselect[0]][0])

        for col in preselect:
            for table in self.lookUp[col]:
                if table in tables:
                    select.append(table + "." + col) #if checked as "SELECT" add to select with table disambiguation from lookup
                    break

        for i in where_filters:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i:
                    for table in self.lookUp[self.columnComments[j][0]]:
                        if table in tables:
                            where.append(table + "." + self.columnComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup

        for i in self.columnComments:
            if i[1] in where_filters:
                numericAllowed = True

                tClause = requestArgs.get('comp_clause_' + i[1])
                tOp = requestArgs.get('comp_op_' + i[1])
                dataType = self.dataTypeByComment[i[1]]
                if tClause != None and tOp != None:
                    try:
                        if tOp.lower() != 'like':
                            if dataType == "double":
                                temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            elif dataType == "int":
                                temp = str(int(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            else:
                                raise ValueError()
                        else:
                            raise ValueError()
                        whereCondition.append(temp)
                    except:
                        if tOp.lower() == 'like':
                            tClause = "%" + QuerryBuilder.escapeString(tClause) + "%"
                        temp = "'" + QuerryBuilder.escapeString(tClause) + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                        numericAllowed = False
                        whereCondition.append(temp)
                    if numericAllowed and tOp in ('=', '>', '<', '>=', '<='):
                        whereSymbol.append(tOp)
                    elif tOp.lower() == 'like':
                        whereSymbol.append(" LIKE ")
                    else:
                        whereSymbol.append("=")

                t = requestArgs.get('rad_' + i[1])
                if t != None:
                    if t == "no":
                        sort = 0
                    elif t == "asc":
                        sort = 1
                        sortCol = i[0]
                    else:
                        sort = 2
                        sortCol = i[0]

        querry += ",".join(select)
        querry += " FROM "
        querry += tables[0] + " "

        counted = [False for i in range(len(tables))]
        counted[0] = True
        
        bfs = []
        bfs.insert(0, QuerryBuilder.TABLES[tables[0]])
        while len(bfs) > 0:
            current = bfs.pop(0)
            for i in range(len(tables)):
                nextV = QuerryBuilder.TABLES[tables[i]]
                joinCol = QuerryBuilder.TABLES_ADJACENCY[current][nextV]
                if joinCol != None and not counted[i]:
                    counted[i] = True
                    bfs.append(nextV)
                    if len(joinCol) == 1:
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON " + QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[0] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[0] + " "
                    else:
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON "
                        for col in range(len(joinCol)):
                            querry += QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[col] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[col] + " AND "
                        querry = querry[:-4]

        if len(where) > 0: #if any filters were checked for "WHERE"
                querry += " WHERE "
                for w in range(len(where)):
                    querry += where[w] + whereSymbol[w] + whereCondition[w] + " AND "
                querry = querry[:-5] #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        if sort == 1:
            querry += " ORDER BY " + sortCol + " ASC" #if ascending sorting was chosen 
        elif sort == 2:
            querry += " ORDER BY " + sortCol + " DESC" #if descending sorting was chosen

        return querry

    def editRetrieveQuerry(self, requestArgs, selected: list) -> str:
        if len(selected) == 0:
            return ""

        querry = "SELECT DISTINCT " #base of querry
        preselect = []
        select = [] #all columns to select
        where = []
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        tables = []

        useWhere = False

        tempSelected = []
        for i in selected:
            if requestArgs.get("inf_" + i) == '0':
                tempSelected.append(i)
        selected = tempSelected
        QuerryBuilder.remaining = tempSelected

        for i in selected:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i:
                    preselect.append(self.columnComments[j][0]) 

        if len(preselect) > 1:
            for i1 in range(len(preselect)-1):
                for i2 in range(i1+1, len(preselect)):
                    tables2 = self.__leastTables(preselect[i1], preselect[i2])
                    for t in tables2:
                        if t not in tables:
                            tables.append(t)
        else:
            tables.append(self.lookUp[preselect[0]][0])

        for col in preselect:
            for table in self.lookUp[col]:
                if table in tables:
                    select.append(table + "." + col) #if checked as "SELECT" add to select with table disambiguation from lookup
                    break
        where = [False for i in range(len(select))]

        order = 0
        for i in self.columnComments:
            numericAllowed = True

            tClause = requestArgs.get('comp_clause_' + i[1])
            tOp = requestArgs.get('comp_op_' + i[1])
            dataType = self.dataTypeByComment[i[1]]
            if tClause != None and tOp != None:
                if tClause != "" and tOp != "":
                    where[order] = True
                    useWhere = True
                order+=1
                try:
                    if tOp.lower() != 'like':
                        if dataType == "double":
                            temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                        elif dataType == "int":
                            temp = str(int(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                        else:
                            raise ValueError()
                    else:
                        raise ValueError()
                    whereCondition.append(temp)
                except:
                    if tOp.lower() == 'like':
                        tClause = "%" + QuerryBuilder.escapeString(tClause) + "%"
                    temp = "'" + QuerryBuilder.escapeString(tClause) + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                    numericAllowed = False
                    whereCondition.append(temp)
                if numericAllowed and tOp in ('=', '>', '<', '>=', '<='):
                    whereSymbol.append(tOp)
                elif tOp.lower() == 'like':
                    whereSymbol.append(" LIKE ")
                else:
                    whereSymbol.append("=")

        querry += ",".join(select)
        querry += " FROM "
        querry += tables[0] + " "
        
        counted = [False for i in range(len(tables))]
        counted[0] = True
        
        bfs = []
        bfs.insert(0, QuerryBuilder.TABLES[tables[0]])
        while len(bfs) > 0:
            current = bfs.pop(0)
            for i in range(len(tables)):
                nextV = QuerryBuilder.TABLES[tables[i]]
                joinCol = QuerryBuilder.TABLES_ADJACENCY[current][nextV]
                if joinCol != None and not counted[i]:
                    counted[i] = True
                    bfs.append(nextV)
                    if len(joinCol) == 1:
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON " + QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[0] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[0] + " "
                    else:
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON "
                        for col in range(len(joinCol)):
                            querry += QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[col] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[col] + " AND "
                        querry = querry[:-4]

        if useWhere:
            querry += " WHERE "
            for w in range(len(select)):
                if where[w]:
                    querry += select[w] + whereSymbol[w] + whereCondition[w] + " AND "
            querry = querry[:-5] + "\n" #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        QuerryBuilder.editSelected = select
        QuerryBuilder.editTables = tables

        return querry
    
    def editExecute(self, changed: list) -> list:
        FullQuerry = []
        for entryOld, entryNew in changed:
            for table in QuerryBuilder.editTables:
                querry = "UPDATE "
                where = "WHERE "
                querry += table + " SET "
                editted = False
                for atr in range(len(entryNew)):
                    seperator = QuerryBuilder.editSelected[atr].find(".")
                    qualifier = QuerryBuilder.editSelected[atr][:seperator]
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:]

                    oldVal = None
                    newVal = None
                    if self.dataTypeByName[atribute] == "double":
                        oldVal = str(float(entryOld[atr]))
                        newVal = str(float(entryNew[atr]))
                    elif self.dataTypeByName[atribute] == "int":
                        oldVal = str(int(entryOld[atr]))
                        newVal = str(float(entryNew[atr]))
                    else:
                        oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        newVal = "'" + QuerryBuilder.escapeString(entryNew[atr]) + "'"
                    if entryNew[atr] == '':
                        newVal = 'NULL'

                    if qualifier == table:
                        querry += QuerryBuilder.editSelected[atr] + " = " + newVal + ", "
                        where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if not editted:
                    querry = querry[:-len(table)]
                else:
                    querry = querry[:-2]
                    where = where[:-5]

                FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    def editExecuteParent(self, changed: list) -> str:
        FullQuerry = []
        for entryOld, entryNew in changed:
            for table in QuerryBuilder.editTables:
                querry = "UPDATE "
                where = "WHERE "
                querry += table + " SET "
                editted = False
                for atr in range(len(entryNew)):
                    seperator = QuerryBuilder.editSelected[atr].find(".")
                    qualifier = QuerryBuilder.editSelected[atr][:seperator]
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:]

                    oldVal = None
                    newVal = None
                    if self.dataTypeByName[atribute] == "double":
                        oldVal = str(float(entryOld[atr]))
                        newVal = str(float(entryNew[atr]))
                    elif self.dataTypeByName[atribute] == "int":
                        oldVal = str(int(entryOld[atr]))
                        newVal = str(float(entryNew[atr]))
                    else:
                        oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        newVal = "'" + QuerryBuilder.escapeString(entryNew[atr]) + "'"
                    if entryNew[atr] == '':
                        newVal = 'NULL'

                    if atribute in QuerryBuilder.PARENT_TABLES:
                        FullQuerry.append("UPDATE " + QuerryBuilder.PARENT_TABLES[atribute] + " SET " + atribute + " = " + newVal + " WHERE " + atribute + " = " + oldVal)

                    elif qualifier == table:
                        querry += QuerryBuilder.editSelected[atr] + " = " + newVal + ", "
                        where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if not editted:
                    break
                else:
                    querry = querry[:-2]
                    where = where[:-5]

                FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    def logQuerry(self, requestArgs, selected: list) -> str:
        selected_filters = requestArgs.getlist('select_filters')
        where_filters = requestArgs.getlist('where_filters')

        if len(selected_filters) == 0:
            return ""

        querry = "SELECT DISTINCT " #base of querry
        select = [] #all columns to select
        where = [] #all columns to include in "WHERE" statement
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        sort = 0
        sortCol = ""

        tempSelected = []
        for i in selected:
            if i in selected_filters or i in where_filters:
                tempSelected.append(i)
        selected = tempSelected
        QuerryBuilder.remaining = tempSelected

        for i in selected_filters:
            for j in range(len(self.logComments)):
                if self.logComments[j][1] == i:
                    select.append(self.logComments[j][0]) 

        for i in where_filters:
            for j in range(len(self.logComments)):
                if self.logComments[j][1] == i:
                    where.append(self.logComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup

        for i in self.logComments:
            if i[1] in where_filters:
                numericAllowed = True

                tClause = requestArgs.get('comp_clause_' + i[1])
                tOp = requestArgs.get('comp_op_' + i[1])
                dataType = self.dataTypeByComment[i[1]]
                if tClause != None and tOp != None:
                    try:
                        if tOp.lower() != 'like':
                            if dataType == "double":
                                temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            elif dataType == "int":
                                temp = str(int(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            else:
                                raise ValueError()
                        else:
                            raise ValueError()
                        whereCondition.append(temp)
                    except:
                        if tOp.lower() == 'like':
                            tClause = "%" + QuerryBuilder.escapeString(tClause) + "%"
                        temp = "'" + QuerryBuilder.escapeString(tClause) + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                        numericAllowed = False
                        whereCondition.append(temp)
                    if numericAllowed and tOp in ('=', '>', '<', '>=', '<='):
                        whereSymbol.append(tOp)
                    elif tOp.lower() == 'like':
                        whereSymbol.append(" LIKE ")
                    else:
                        whereSymbol.append("=")

                t = requestArgs.get('rad_' + i[1])
                if t != None:
                    if t == "no":
                        sort = 0
                    elif t == "asc":
                        sort = 1
                        sortCol = i[0]
                    else:
                        sort = 2
                        sortCol = i[0]

        querry += ",".join(select)
        querry += " FROM logs "

        if len(where) > 0: #if any filters were checked for "WHERE"
                querry += " WHERE "
                for w in range(len(where)):
                    querry += where[w] + whereSymbol[w] + whereCondition[w] + " AND "
                querry = querry[:-5] #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        if sort == 1:
            querry += " ORDER BY " + sortCol + " ASC" #if ascending sorting was chosen 
        elif sort == 2:
            querry += " ORDER BY " + sortCol + " DESC" #if descending sorting was chosen

        return querry
    
    def addQuerry(self, requestArgs) -> list:
        FullQuerry = []
        tempSelect = []
        insertedTables = []
        for table in QuerryBuilder.TABLE_PRIORITY:
            query = "INSERT INTO " + table
            cols = []
            record = []
            empty = True
            for entry in self.tableCols[self.tablesForTableCols.index(table)]:
                colName = entry[0]
                comment = entry[1]
                value = requestArgs.get(comment)
                if value == None:
                    continue
                elif value == "":
                    tempSelect.append(entry[1])
                    continue
                if entry[2] == "varchar":
                    value = "'" + QuerryBuilder.escapeString(value) + "'"
                cols.append(colName)
                record.append(value)
                tempSelect.append(entry[1])
                if not colName == "PRODUCT_ID":
                    empty = False
            if not empty:
                query += "(" + ", ".join(cols) + ") VALUES (" + ", ".join(record) + ")"
                FullQuerry.append(query)
                insertedTables.append(table)
        tempSelect = list(set(tempSelect))
        return FullQuerry, tempSelect, insertedTables

    def addQuerryAlt(self, requestArgs) -> list:
        FullQuerry = []
        for table in QuerryBuilder.TABLE_PRIORITY:
            query = "INSERT INTO " + table
            cols = []
            record = []
            empty = True
            for entry in self.tableCols[self.tablesForTableCols.index(table)]:
                colName = entry[0]
                if requestArgs.get("changed_" + table + "_" + colName) == "0" and not colName == "PRODUCT_ID":
                    continue
                value = requestArgs.get(table + "_" + colName)
                if entry[2] == "varchar":
                    value = "'" + value + "'"
                cols.append(colName)
                record.append(value)
                if not colName == "PRODUCT_ID":
                    empty = False
            if not empty:
                query += "(" + ", ".join(cols) + ") VALUES (" + ", ".join(record) + ")"
                FullQuerry.append(query)
        return FullQuerry

    def deleteExecute(self, changed: list) -> list:
        FullQuerry = []
        for entryOld in changed:
            for table in QuerryBuilder.editTables:
                querry = "DELETE FROM "
                where = "WHERE "
                querry += table + " "
                editted = False
                for atr in range(len(entryOld)):
                    seperator = QuerryBuilder.editSelected[atr].find(".")
                    qualifier = QuerryBuilder.editSelected[atr][:seperator]
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:]

                    oldVal = None
                    if self.dataTypeByName[atribute] == "double":
                        oldVal = str(float(entryOld[atr]))
                    elif self.dataTypeByName[atribute] == "int":
                        oldVal = str(int(entryOld[atr]))
                    else:
                        oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        
                    if qualifier == table:
                        where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if not editted:
                    querry = querry[:-len(table)]
                else:
                    where = where[:-5]

                FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    def deleteExecuteParent(self, changed: list) -> str:
        FullQuerry = []
        for entryOld in changed:
            for table in QuerryBuilder.editTables:
                querry = "DELETE FROM "
                where = "WHERE "
                querry += table + " "
                editted = False
                for atr in range(len(entryOld)):
                    seperator = QuerryBuilder.editSelected[atr].find(".")
                    qualifier = QuerryBuilder.editSelected[atr][:seperator]
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:]
                    
                    oldVal = None
                    if self.dataTypeByName[atribute] == "double":
                        oldVal = str(float(entryOld[atr]))
                    elif self.dataTypeByName[atribute] == "int":
                        oldVal = str(int(entryOld[atr]))
                    else:
                        oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"

                    if atribute in QuerryBuilder.PARENT_TABLES:
                        FullQuerry.append("DELETE FROM " + QuerryBuilder.PARENT_TABLES[atribute] + " WHERE " + atribute + " = " + oldVal)

                    elif qualifier == table:
                        where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if not editted:
                    break
                else:
                    where = where[:-5]

                FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    def updateToDelete(self, query: str) -> str:
        return "DELETE FROM " + query.split()[1] + " " + query[query.find("WHERE"):]
