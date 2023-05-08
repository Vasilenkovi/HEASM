

class QuerryBuilder():

    lookUp = []
    columnComments = []

    TABLES = {"bib_source": 0, "bibliography": 1, "countries": 2, "ingredients": 3, "key_word": 4, "measurements": 5, "synthesis_parameter": 6, "synthesis_product": 7}
    TABLES_INVERSE = ["bib_source", "bibliography", "countries", "ingredients", "key_word", "measurements", "synthesis_parameter", "synthesis_product"]

    TABLES_ADJACENCY = [
        [None, 'JOURNAL', None, None, None, None, None, None],
        ['JOURNAL', None, 'DOI', None, 'DOI', None, None, 'DOI'],
        [None, 'DOI', None, None, None, None, None, None],
        [None, None, None, None, None, None, None, 'PRODUCT_ID'],
        [None, 'DOI', None, None, None, None, None, None],
        [None, None, None, None, None, None, None, 'PRODUCT_ID'],
        [None, None, None, None, None, None, None, 'PRODUCT_ID'],
        [None, 'DOI', None, 'PRODUCT_ID', None, 'PRODUCT_ID', 'PRODUCT_ID', None]
    ]

    def __init__(self, in_lookUp: dict, in_columnComments: list) -> None:
        self.lookUp = in_lookUp
        self.columnComments = in_columnComments

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

        for i in where_filters:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i:
                    for table in self.lookUp[self.columnComments[j][0]]:
                        if table in tables:
                            where.append(table + "." + self.columnComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup

        for i in self.columnComments:
            numericAllowed = True

            tClause = requestArgs.get('comp_clause_' + i[1])
            tOp = requestArgs.get('comp_op_' + i[1])
            if tClause != None and tOp != None:
                try:
                    temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                    whereCondition.append(temp)
                except:
                    if tOp.lower() == 'like':
                        tClause = "%" + tClause + "%"
                    temp = "'" + tClause + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
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
        for i in range(1, len(tables)):
            left = QuerryBuilder.TABLES[tables[i]]
            right = QuerryBuilder.TABLES[tables[i-1]]
            joinCol = QuerryBuilder.TABLES_ADJACENCY[left][right]
            if joinCol != None:
                querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[left] + " ON " + QuerryBuilder.TABLES_INVERSE[right] + "." + joinCol + " = " + QuerryBuilder.TABLES_INVERSE[left] + "." + joinCol + " "
            else:
                for j in range(len(tables)):
                    left = QuerryBuilder.TABLES[tables[i]]
                    right = QuerryBuilder.TABLES[tables[j]]
                    joinCol = QuerryBuilder.TABLES_ADJACENCY[left][right]
                    if joinCol != None:
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[left] + " ON " + QuerryBuilder.TABLES_INVERSE[right] + "." + joinCol + " = " + QuerryBuilder.TABLES_INVERSE[left] + "." + joinCol + " "

        if len(where) > 0: #if any filters were checked for "WHERE"
                querry += " WHERE "
                for w in range(len(where)):
                    querry += where[w] + whereSymbol[w] + whereCondition[w] + " AND "
                querry = querry[:-5] + "\n" #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        if sort == 1:
            querry += "ORDER BY " + sortCol + " ASC" #if ascending sorting was chosen 
        elif sort == 2:
            querry += "ORDER BY " + sortCol + " DESC" #if descending sorting was chosen

        return querry

    def editRetrieveQuerry(self, requestArgs, selected: list) -> str:
        if len(selected) == 0:
            return ""

        querry = "SELECT " #base of querry
        preselect = []
        select = [] #all columns to select
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        tables = []

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

        for i in self.columnComments:
            numericAllowed = True

            tClause = requestArgs.get('comp_clause_' + i[1])
            tOp = requestArgs.get('comp_op_' + i[1])
            if tClause != None and tOp != None:
                try:
                    temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                    whereCondition.append(temp)
                except:
                    if tOp.lower() == 'like':
                        tClause = "%" + tClause + "%"
                    temp = "'" + tClause + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
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
        for i in range(1, len(tables)):
            left = QuerryBuilder.TABLES[tables[i]]
            right = QuerryBuilder.TABLES[tables[i-1]]
            joinCol = QuerryBuilder.TABLES_ADJACENCY[left][right]
            if joinCol != None:
                querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[left] + " ON " + QuerryBuilder.TABLES_INVERSE[right] + "." + joinCol + " = " + QuerryBuilder.TABLES_INVERSE[left] + "." + joinCol + " "
            else:
                for j in range(len(tables)):
                    left = QuerryBuilder.TABLES[tables[i]]
                    right = QuerryBuilder.TABLES[tables[j]]
                    joinCol = QuerryBuilder.TABLES_ADJACENCY[left][right]
                    if joinCol != None:
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[left] + " ON " + QuerryBuilder.TABLES_INVERSE[right] + "." + joinCol + " = " + QuerryBuilder.TABLES_INVERSE[left] + "." + joinCol + " "

        
        querry += " WHERE "
        for w in range(len(select)):
            querry += select[w] + whereSymbol[w] + whereCondition[w] + " AND "
        querry = querry[:-5] + "\n" #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        return querry