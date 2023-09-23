from markupsafe import escape
class QuerryBuilder():

    lookUp = {} #lookUp dict for column-table disambiguation
    columnComments = [] #List of columns with repective comments and data types 
    logComments = [] #Columns for 'logs' table
    editSelected = [] #Storage for selected filters for edit
    editTables = [] #Storage for tables being edited
    remaining = [] #Storage for selected filters, after user dropped some
    dataTypeByComment = {} #Dict mapping column comments to data types
    dataTypeByName = {} #Dict mapping column names to data types

    TABLES = {"bib_source": 0, "bibliography": 1, "countries": 2, "ingredients": 3, "key_word": 4, "measurements": 5, "synthesis_parameter": 6, "synthesis_product": 7} #Tables in order of adjacency matrix
    TABLES_INVERSE = ["bib_source", "bibliography", "countries", "ingredients", "key_word", "measurements", "synthesis_parameter", "synthesis_product"] #Tables in order of adjacency matrix. Inversed to access table by index

    #Adjacency matrix of tables, containing atributes for joining
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

    PARENT_TABLES = {"YEAR": "bib_source", "JOURNAL": "bib_source", "DOI": "bibliography", "PRODUCT_ID": "synthesis_product"} #What tables to update when atribute breaks foreign key constraint
    TABLE_PRIORITY = ["bib_source", "bibliography", "key_word", "countries", "synthesis_product", "ingredients", "measurements", "synthesis_parameter"] #DML order to follow foreign key constraint

    def __init__(self, in_lookUp: dict, in_columnComments: list, in_logComments: list, in_tablesForTableCols: list, in_tableCols: list, in_dataTypeByComment: dict, in_dataTypeByName: dict) -> None:
        self.lookUp = in_lookUp
        self.columnComments = in_columnComments
        self.logComments = in_logComments
        self.tablesForTableCols = in_tablesForTableCols
        self.tableCols = in_tableCols
        self.dataTypeByComment = in_dataTypeByComment
        self.dataTypeByName = in_dataTypeByName

    #Auxiliary method to escape some special characters
    def escapeString(string: str) -> str:
        res = r""
        for c in string: #for character in string
            if c in ('"', "'", ";", "%", "_"): #if character needs to be escaped
                res += "\{}".format(c)
            else:
                res += c
        return res

    #Returns least amount of tables to select to access both atributes
    def __leastTables(self, col1, col2) -> list:
        for i in self.lookUp[col1]:
            for j in self.lookUp[col2]:
                if i == j: #If sets of tables of two atributes intersect, both atributes can be accessed from intersecting table
                    return [i]
        #Else BFS to find shortest path in table graph (connect atributes by joining least tables)
        table1 = self.lookUp[col1][0] #Table containing 1 atribute
        table2 = self.lookUp[col2][0] #Table containing 2 atribute
        queue = [] #Queue for BFS
        queue.append(QuerryBuilder.TABLES[table1]) #Starting vertex
        visited = [False for i in range(8)] #None visited
        visited[QuerryBuilder.TABLES[table1]] = True #Actually, starting vertex was visited
        prev = [-1 for i in range(8)] #Previous vertex on path to i

        while len(queue) > 0:
            v = queue.pop(0) #Select next vertex
            for i in range(8): #Check every table
                if QuerryBuilder.TABLES_ADJACENCY[v][i] != None and not visited[i]: #If edge to next table exists and it wasn't visited
                    queue.append(i) #Add vertex
                    visited[i] = True #Now visited
                    prev[i] = v #Got here through v vertex
                    if i == QuerryBuilder.TABLES[table2]: #If path ends where needed
                        queue.clear() #Clear queue to end BFS
                        break

        out = [] #Table path in order
        current = table2
        out.append(current)
        while current != table1: #While path is not complete
            current = QuerryBuilder.TABLES_INVERSE[prev[QuerryBuilder.TABLES[current]]] #Calculate index for previous to current table in path
            out.append(current)

        return out

    #SELECT query
    def buildQuerry(self, requestArgs, selected: list) -> str:
        selected_filters = list(map(lambda x: str(escape(x)), requestArgs.getlist('select_filters'))) #Get all checked for SELECT
        where_filters = list(map(lambda x: str(escape(x)), requestArgs.getlist('where_filters'))) #Get all checked for WHERE

        if len(selected_filters) == 0: #If none are going to be displayed
            return ""

        querry = "SELECT DISTINCT " #base of querry
        preselect = [] #all columns to select without table qualifier
        select = [] #all columns to select
        where = [] #all columns to include in "WHERE" statement
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        sort = 0 #Directon to sort (0 = no sort)
        sortCol = "" #Sorting column
        tables = [] #Tables needed to be selected

        tempSelected = [] #Filters that remain selected after user may have dropped some
        for i in selected: 
            if i in selected_filters or i in where_filters: #If filter is still in form
                tempSelected.append(i)
        selected = tempSelected #Reassign selected 
        QuerryBuilder.remaining = tempSelected #Reassign selected 

        for i in selected_filters:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i: #if selected filter equals comment on a column
                    preselect.append(self.columnComments[j][0]) #Add column name to preselect

        if len(preselect) > 1: #If several columns were chosen, find least amount of tables needed to be joined
            for i1 in range(len(preselect)-1): 
                for i2 in range(i1+1, len(preselect)):
                    tables2 = self.__leastTables(preselect[i1], preselect[i2]) #Least tables from every atribute to every atribute
                    for t in tables2:
                        if t not in tables: #If table not already in list
                            tables.append(t)
        else:
            tables.append(self.lookUp[preselect[0]][0]) #If only one column selected, use a single table with column

        for col in preselect: #Loop through preselect
            for table in self.lookUp[col]: #Loop through tables containing column
                if table in tables:
                    select.append(table + "." + col) #if checked as "SELECT" add to select with table disambiguation from lookup
                    break

        for i in where_filters:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i: #if selected filter equals comment on a column
                    for table in self.lookUp[self.columnComments[j][0]]:
                        if table in tables: #Find selected table, containing column
                            where.append(table + "." + self.columnComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup

        for i in self.columnComments: #For every possible filter
            if i[1] in where_filters: #if marked for where
                numericAllowed = True #Assume numeric input

                tClause = str(escape(requestArgs.get('comp_clause_' + i[1]))) #Get expression to compare to
                tOp = requestArgs.get('comp_op_' + i[1]) #Get comparison operator
                dataType = self.dataTypeByComment[i[1]] #Get data type for column
                if tClause != 'None' and tOp != 'None': #if data supplied
                    try:
                        if tOp.lower() != 'like': #if numeric operator supplied
                            if dataType == "double":
                                temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            elif dataType == "int":
                                temp = str(int(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            else:
                                raise ValueError() #if numeric operator used with string
                        else:
                            raise ValueError() #Shortcut to string data processing
                        whereCondition.append(temp)
                    except:
                        if tOp.lower() == 'like':
                            tClause = "%" + QuerryBuilder.escapeString(tClause) + "%" #wrap string in wildcards to match everywhere
                        temp = "'" + QuerryBuilder.escapeString(tClause) + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                        numericAllowed = False #Since defaulted to string condition
                        whereCondition.append(temp)
                    if numericAllowed and tOp in ('=', '>', '<', '>=', '<='):
                        whereSymbol.append(tOp)
                    elif tOp.lower() == 'like':
                        whereSymbol.append(" LIKE ")
                    else:
                        whereSymbol.append("=")

                t = str(escape(requestArgs.get('rad_' + i[1]))) #Get sorting state
                if t != 'None':
                    if t == "no":
                        sort = 0
                    elif t == "asc":
                        sort = 1
                        sortCol = i[0] #will be sorted along this column
                    else:
                        sort = 2
                        sortCol = i[0] #will be sorted along this column

        querry += ",".join(select) #All selected columns joined
        querry += " FROM "
        querry += tables[0] + " "

        counted = [False for i in range(len(tables))] #No tables were selected yet
        counted[0] = True #Actualy, first table already selected
        
        bfs = [] #Queue for DFS among selected tables to join them all
        bfs.insert(0, QuerryBuilder.TABLES[tables[0]]) #Starting table
        while len(bfs) > 0:
            current = bfs.pop(0)
            for i in range(len(tables)):
                nextV = QuerryBuilder.TABLES[tables[i]] #Next table
                joinCol = QuerryBuilder.TABLES_ADJACENCY[current][nextV] #columns that link next table to last
                if joinCol != None and not counted[i]: #if edge exists and table is not accounted for
                    counted[i] = True 
                    bfs.append(nextV)
                    if len(joinCol) == 1: #if next table is joined to last with one column
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON " + QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[0] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[0] + " "
                    else: #if next table is joined to last with more than one column
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON "
                        for col in range(len(joinCol)):
                            querry += QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[col] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[col] + " AND "
                        querry = querry[:-4] #Remove last AND

        if len(where) > 0: #if any filters were checked for "WHERE"
                querry += " WHERE "
                for w in range(len(where)): #For every complete 'where'
                    querry += where[w] + whereSymbol[w] + whereCondition[w] + " AND "
                querry = querry[:-5] #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        if sort == 1:
            querry += " ORDER BY " + sortCol + " ASC" #if ascending sorting was chosen 
        elif sort == 2:
            querry += " ORDER BY " + sortCol + " DESC" #if descending sorting was chosen

        return querry

    #Query to retrieve data for edit or delete
    def editRetrieveQuerry(self, requestArgs, selected: list) -> str:
        if len(selected) == 0: #If none are going to be displayed
            return ""

        querry = "SELECT DISTINCT " #base of querry
        preselect = [] #all columns to select without table qualifier
        select = [] #all columns to select
        where = [] #all columns to include in "WHERE" statement
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        tables = [] #Tables needed to be selected

        useWhere = False #Assume non zero amount of 'where' filters

        tempSelected = [] #Filters that remain selected after user may have dropped some
        for i in selected:
            if str(escape(requestArgs.get("inf_" + i))) == '0': #If filter is still in form
                tempSelected.append(i)
        selected = tempSelected #Reassign selected 
        QuerryBuilder.remaining = tempSelected #Reassign selected 
 
        for i in selected:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i: #if selected filter equals comment on a column
                    preselect.append(self.columnComments[j][0]) #Add column name to preselect

        if len(preselect) > 1: #If several columns were chosen, find least amount of tables needed to be joined
            for i1 in range(len(preselect)-1): 
                for i2 in range(i1+1, len(preselect)):
                    tables2 = self.__leastTables(preselect[i1], preselect[i2]) #Least tables from every atribute to every atribute
                    for t in tables2:
                        if t not in tables: #If table not already in list
                            tables.append(t)
        else:
            tables.append(self.lookUp[preselect[0]][0])

        for col in preselect: #Loop through preselect
            for table in self.lookUp[col]: #Loop through tables containing column
                if table in tables:
                    select.append(table + "." + col) #if checked as "SELECT" add to select with table disambiguation from lookup
                    break
        where = [False for i in range(len(select))] #Assume no 'where' conditions were specified for selected columns

        order = 0 #Keep track of actually selected and user-inputed columns
        for i in self.columnComments: #For every possible column
            numericAllowed = True #Assume numeric input

            tClause = str(escape(requestArgs.get('comp_clause_' + i[1]))) #Get where expression
            tOp = requestArgs.get('comp_op_' + i[1]) #Get comparisson operator
            dataType = self.dataTypeByComment[i[1]] #Get column data type
            if tClause != 'None' and tOp != 'None': #if filter is in form
                if tClause != "" and tOp != "": 
                    where[order] = True
                    useWhere = True
                order+=1
                try:
                    if tOp.lower() != 'like': #if numeric operator supplied
                        if dataType == "double":
                            temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                        elif dataType == "int":
                            temp = str(int(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                        else:
                            raise ValueError() #if numeric operator used with string
                    else:
                        raise ValueError() #Shortcut to string data processing
                    whereCondition.append(temp)
                except:
                    if tOp.lower() == 'like':
                        tClause = "%" + QuerryBuilder.escapeString(tClause) + "%" #wrap string in wildcards to match everywhere
                    temp = "'" + QuerryBuilder.escapeString(tClause) + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                    numericAllowed = False  #Since defaulted to string condition
                    whereCondition.append(temp)
                if numericAllowed and tOp in ('=', '>', '<', '>=', '<='):
                    whereSymbol.append(tOp)
                elif tOp.lower() == 'like':
                    whereSymbol.append(" LIKE ")
                else:
                    whereSymbol.append("=")

        querry += ",".join(select) #All selected columns joined
        querry += " FROM "
        querry += tables[0] + " "

        counted = [False for i in range(len(tables))] #No tables were selected yet
        counted[0] = True #Actualy, first table already selected
        
        bfs = [] #Queue for DFS among selected tables to join them all
        bfs.insert(0, QuerryBuilder.TABLES[tables[0]]) #Starting table
        while len(bfs) > 0:
            current = bfs.pop(0)
            for i in range(len(tables)):
                nextV = QuerryBuilder.TABLES[tables[i]] #Next table
                joinCol = QuerryBuilder.TABLES_ADJACENCY[current][nextV] #columns that link next table to last
                if joinCol != None and not counted[i]: #if edge exists and table is not accounted for
                    counted[i] = True 
                    bfs.append(nextV)
                    if len(joinCol) == 1: #if next table is joined to last with one column
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON " + QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[0] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[0] + " "
                    else: #if next table is joined to last with more than one column
                        querry += "INNER JOIN " + QuerryBuilder.TABLES_INVERSE[nextV] + " ON "
                        for col in range(len(joinCol)):
                            querry += QuerryBuilder.TABLES_INVERSE[current] + "." + joinCol[col] + " = " + QuerryBuilder.TABLES_INVERSE[nextV] + "." + joinCol[col] + " AND "
                        querry = querry[:-4] #Remove last AND

        if useWhere: #if some columns were checjed for 'where'
            querry += " WHERE "
            for w in range(len(select)):
                if where[w]:
                    querry += select[w] + whereSymbol[w] + whereCondition[w] + " AND "
            querry = querry[:-5] + "\n" #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        QuerryBuilder.editSelected = select #Save columns that were edited
        QuerryBuilder.editTables = tables #Save tables that were edited

        return querry
    
    #Actually applies UPDATE
    def editExecute(self, changed: list) -> list:
        FullQuerry = [] #List of small, table-wide, single row updates
        for entryOld, entryNew in changed: #Chabged is supplied as a list of [[old row], [new row]]
            for table in QuerryBuilder.editTables: #For every saved table
                querry = "UPDATE "
                where = "WHERE "
                querry += table + " SET "
                editted = False #Assume no columns were edited for table
                for atr in range(len(entryNew)): #For each atribute from selection
                    seperator = QuerryBuilder.editSelected[atr].find(".") #From cached columns get table_name.column_name
                    qualifier = QuerryBuilder.editSelected[atr][:seperator] #Table name
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:] #Column name

                    oldVal = None
                    newVal = None
                    oldAsNull = False #Wether or not to interpret as NULL
                    if entryNew[atr] == '': #Interpret empty string as NULL
                        newVal = 'NULL'
                    else:
                        try: #Try casting to appropriate data type
                            if self.dataTypeByName[atribute] == "double":
                                newVal = str(float(entryNew[atr]))
                            elif self.dataTypeByName[atribute] == "int":
                                newVal = str(float(entryNew[atr]))
                            else:
                                newVal = "'" + QuerryBuilder.escapeString(entryNew[atr]) + "'"
                        except: #Wrong data Type
                            raise ValueError()
                    if entryOld[atr] == '': #Interpret empty string as NULL
                        oldVal = 'NULL'
                        oldAsNull = True
                    else:
                        try: #Try casting to appropriate data type
                            if self.dataTypeByName[atribute] == "double":
                                oldVal = str(float(entryOld[atr]))
                            elif self.dataTypeByName[atribute] == "int":
                                oldVal = str(int(entryOld[atr]))
                            else:
                                oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        except: #Wrong data Type
                            raise ValueError()

                    if qualifier == table: #If atribute is in table
                        querry += QuerryBuilder.editSelected[atr] + " = " + newVal + ", "
                        if oldAsNull:
                            where += QuerryBuilder.editSelected[atr] + " IS " + oldVal + " AND "
                        else:
                            where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if editted:
                    querry = querry[:-2] #Remove last ", "
                    where = where[:-5] #Remove last " AND "
                    FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    #Applies UPDATE when foreign key constraint fails
    def editExecuteParent(self, changed: list) -> str:
        FullQuerry = [] #List of small, table-wide, single row updates
        for entryOld, entryNew in changed: #Chabged is supplied as a list of [[old row], [new row]]
            for table in QuerryBuilder.editTables: #For every saved table
                querry = "UPDATE "
                where = "WHERE "
                querry += table + " SET "
                editted = False #Assume no columns were edited for table
                for atr in range(len(entryNew)): #For each atribute from selection
                    seperator = QuerryBuilder.editSelected[atr].find(".") #From cached columns get table_name.column_name
                    qualifier = QuerryBuilder.editSelected[atr][:seperator] #Table name
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:] #Column name

                    oldVal = None
                    newVal = None
                    oldAsNull = False #Wether or not to interpret as NULL
                    if entryNew[atr] == '': #Interpret empty string as NULL
                        newVal = 'NULL'
                    else:
                        try: #Try casting to appropriate data type
                            if self.dataTypeByName[atribute] == "double":
                                newVal = str(float(entryNew[atr]))
                            elif self.dataTypeByName[atribute] == "int":
                                newVal = str(float(entryNew[atr]))
                            else:
                                newVal = "'" + QuerryBuilder.escapeString(entryNew[atr]) + "'"
                        except: #Wrong data Type
                            raise ValueError()
                    if entryOld[atr] == '': #Interpret empty string as NULL
                        oldVal = 'NULL'
                        oldAsNull = True
                    else:
                        try: #Try casting to appropriate data type
                            if self.dataTypeByName[atribute] == "double":
                                oldVal = str(float(entryOld[atr]))
                            elif self.dataTypeByName[atribute] == "int":
                                oldVal = str(int(entryOld[atr]))
                            else:
                                oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        except: #Wrong data Type
                            raise ValueError()

                    if atribute in QuerryBuilder.PARENT_TABLES: #If atribute could break foreign key constraint, update parent tables first
                        whereStr = ""
                        atrStr = atribute + " = " + newVal
                        if oldAsNull:
                            whereStr = atribute + " IS " + oldVal
                        else:
                            whereStr = atribute + " = " + oldVal
                        FullQuerry.append("UPDATE " + QuerryBuilder.PARENT_TABLES[atribute] + " SET " + atrStr + " WHERE " + whereStr)

                    elif qualifier == table: #If atribute is in table
                        querry += QuerryBuilder.editSelected[atr] + " = " + newVal + ", "
                        if oldAsNull:
                            where += QuerryBuilder.editSelected[atr] + " IS " + oldVal + " AND "
                        else:
                            where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if editted:
                    querry = querry[:-2] #Remove last ", "
                    where = where[:-5] #Remove last " AND "
                    FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    #Query to retrieve logs
    def logQuerry(self, requestArgs, selected: list) -> str:
        selected_filters = list(map(lambda x: str(escape(x)), requestArgs.getlist('select_filters'))) #Get all checked for SELECT
        where_filters = list(map(lambda x: str(escape(x)), requestArgs.getlist('where_filters'))) #Get all checked for WHERE

        if len(selected_filters) == 0: #If none are going to be displayed
            return ""

        querry = "SELECT DISTINCT " #base of querry
        select = [] #all columns to select
        where = [] #all columns to include in "WHERE" statement
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions
        sort = 0 #Directon to sort (0 = no sort)
        sortCol = "" #Sorting column

        tempSelected = [] #Filters that remain selected after user may have dropped some
        for i in selected: 
            if i in selected_filters or i in where_filters: #If filter is still in form
                tempSelected.append(i)
        selected = tempSelected #Reassign selected 
        QuerryBuilder.remaining = tempSelected #Reassign selected 

        for i in selected_filters:
            for j in range(len(self.logComments)):
                if self.logComments[j][1] == i: #if selected filter equals comment on a column
                    select.append(self.logComments[j][0]) #Add column name to preselect

        for i in where_filters:
            for j in range(len(self.logComments)):
                if self.logComments[j][1] == i:
                    where.append(self.logComments[j][0]) #if checked as "WHERE" add to select with table disambiguation from lookup

        for i in self.logComments: #For every log comment
            if i[1] in where_filters: #If column selected for where
                numericAllowed = True #Assume numeric data

                tClause = str(escape(requestArgs.get('comp_clause_' + i[1]))) #Get expression to compare to
                tOp = requestArgs.get('comp_op_' + i[1]) #Get comparison operator
                dataType = self.dataTypeByComment[i[1]] #Get data type for column
                if tClause != 'None' and tOp != 'None': #if data supplied
                    try:
                        if tOp.lower() != 'like': #if numeric operator supplied
                            if dataType == "double":
                                temp = str(float(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            elif dataType == "int":
                                temp = str(int(tClause)) #if a number was supplied as condition, comparison operators have meaning and are allowed
                            else:
                                raise ValueError() #if numeric operator used with string
                        else:
                            raise ValueError() #Shortcut to string data processing
                        whereCondition.append(temp)
                    except:
                        if tOp.lower() == 'like':
                            tClause = "%" + QuerryBuilder.escapeString(tClause) + "%" #wrap string in wildcards to match everywhere
                        temp = "'" + QuerryBuilder.escapeString(tClause) + "'" #if a string was supplied as condition, comparison operators, aside from '=', have no meaning and are defaulted to '='. Also quotation marks are provided
                        numericAllowed = False #Since defaulted to string condition
                        whereCondition.append(temp)
                    if numericAllowed and tOp in ('=', '>', '<', '>=', '<='):
                        whereSymbol.append(tOp)
                    elif tOp.lower() == 'like':
                        whereSymbol.append(" LIKE ")
                    else:
                        whereSymbol.append("=")

                t = str(escape(requestArgs.get('rad_' + i[1]))) #Get sorting state
                if t != 'None':
                    if t == "no":
                        sort = 0
                    elif t == "asc":
                        sort = 1
                        sortCol = i[0] #will be sorted along this column
                    else:
                        sort = 2
                        sortCol = i[0] #will be sorted along this column

        querry += ",".join(select)
        querry += " FROM logs "

        if len(where) > 0: #if any filters were checked for "WHERE"
                querry += " WHERE "
                for w in range(len(where)): #For every complete 'where'
                    querry += where[w] + whereSymbol[w] + whereCondition[w] + " AND "
                querry = querry[:-5] #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        if sort == 1:
            querry += " ORDER BY " + sortCol + " ASC" #if ascending sorting was chosen 
        elif sort == 2:
            querry += " ORDER BY " + sortCol + " DESC" #if descending sorting was chosen

        return querry
    
    #Query to add content to db
    def addQuerry(self, requestArgs) -> list:
        FullQuerry = [] #List of small, table-wide, single row updates
        tempSelect = [] #List of remaining selected columns
        insertedTables = [] #Tables acted upon in insertion
        for table in QuerryBuilder.TABLE_PRIORITY: #For each table in DML order
            query = "INSERT INTO " + table
            cols = []
            record = []
            empty = True #Assume nothing inserted
            for entry in self.tableCols[self.tablesForTableCols.index(table)]: #For every column in table
                colName = entry[0]
                comment = entry[1]
                value = str(escape(requestArgs.get(comment)))
                if value == 'None': #If column doesn't exist in form
                    continue
                elif value == "": #If no value entered
                    tempSelect.append(entry[1])
                    continue
                if entry[2] == "varchar":
                    value = "'" + QuerryBuilder.escapeString(value) + "'" #If string is expected, wrap it in ''
                cols.append(colName)
                record.append(value)
                tempSelect.append(entry[1])
                if not colName == "PRODUCT_ID": #Prevent from inserting only PRODUCT_ID
                    empty = False
            if not empty: 
                query += "(" + ", ".join(cols) + ") VALUES (" + ", ".join(record) + ")"
                FullQuerry.append(query) 
                insertedTables.append(table) #Saving tables which were inserted into
        tempSelect = list(set(tempSelect)) #Updating selected columns
        return FullQuerry, tempSelect, insertedTables

    def addQuerryAlt(self, requestArgs) -> list:
        FullQuerry = [] #List of small, table-wide, single row updates
        for table in QuerryBuilder.TABLE_PRIORITY: #For each table in DML order
            query = "INSERT INTO " + table
            cols = []
            record = []
            empty = True #Assume nothing inserted
            for entry in self.tableCols[self.tablesForTableCols.index(table)]: #For every column in table
                colName = entry[0]
                if str(escape(requestArgs.get("changed_" + table + "_" + colName))) == "0" and not colName == "PRODUCT_ID": #If not inputed
                    continue
                value = str(escape(requestArgs.get(table + "_" + colName)))
                if entry[2] == "varchar":
                    value = "'" + value + "'" #Wrap string in ''
                cols.append(colName)
                record.append(value)
                if not colName == "PRODUCT_ID": #Prevent from inserting only PRODUCT_ID
                    empty = False
            if not empty:
                query += "(" + ", ".join(cols) + ") VALUES (" + ", ".join(record) + ")"
                FullQuerry.append(query)
        return FullQuerry

    def deleteExecute(self, changed: list, toDeleteColumns: list) -> list:
        FullQuerry = [] #List of small, table-wide, single row updates
        AccountColumns = [] #Actual columns marked for deletion

        for i in toDeleteColumns:
            for j in range(len(self.columnComments)):
                if self.columnComments[j][1] == i: #if selected filter equals comment on a column
                    AccountColumns.append(self.columnComments[j][0]) #Add column name to preselect

        for entryOld in changed: #Changed is supplied as a list
            for table in QuerryBuilder.editTables: #For every saved table
                querry = "DELETE FROM "
                where = "WHERE "
                querry += table + " "
                editted = False #Assume no columns were edited for table
                for atr in range(len(entryOld)): #For each atribute from selection
                    seperator = QuerryBuilder.editSelected[atr].find(".") #From cached columns get table_name.column_name
                    qualifier = QuerryBuilder.editSelected[atr][:seperator] #Table name
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:] #Column name

                    if atribute not in AccountColumns:
                        continue

                    oldVal = None
                    oldAsNull = False #Wether or not to interpret as NULL
                    if entryOld[atr] == '': #Interpret empty string as NULL
                        oldVal = 'NULL'
                        oldAsNull = True
                    else:
                        try:
                            if self.dataTypeByName[atribute] == "double":
                                oldVal = str(float(entryOld[atr]))
                            elif self.dataTypeByName[atribute] == "int":
                                oldVal = str(int(entryOld[atr]))
                            else:
                                oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        except: #Wrong data Type
                            raise ValueError()
                        
                    if qualifier == table: #If atribute is in table
                        if oldAsNull:
                            where += QuerryBuilder.editSelected[atr] + " IS " + oldVal + " AND "
                        else:
                            where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if editted:
                    where = where[:-5] #Remove last " AND "
                    FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    def deleteExecuteParent(self, changed: list) -> str:
        FullQuerry = [] #List of small, table-wide, single row updates
        for entryOld in changed: #Changed is supplied as a list
            for table in QuerryBuilder.editTables: #For every saved table
                querry = "DELETE FROM "
                where = "WHERE "
                querry += table + " "
                editted = False #Assume no columns were edited for table
                for atr in range(len(entryOld)): #For each atribute from selection
                    seperator = QuerryBuilder.editSelected[atr].find(".") #From cached columns get table_name.column_name
                    qualifier = QuerryBuilder.editSelected[atr][:seperator] #Table name
                    atribute = QuerryBuilder.editSelected[atr][seperator+1:] #Column name
                    
                    oldVal = None
                    oldAsNull = False #Wether or not to interpret as NULL
                    if entryOld[atr] == '': #Interpret empty string as NULL
                        oldVal = 'NULL'
                        oldAsNull = True
                    else:
                        try:
                            if self.dataTypeByName[atribute] == "double":
                                oldVal = str(float(entryOld[atr]))
                            elif self.dataTypeByName[atribute] == "int":
                                oldVal = str(int(entryOld[atr]))
                            else:
                                oldVal = "'" + QuerryBuilder.escapeString(entryOld[atr]) + "'"
                        except: #Wrong data Type
                            raise ValueError()

                    if atribute in QuerryBuilder.PARENT_TABLES: #If atribute could have broken foreign key constraint, update paret table first
                        if oldAsNull:
                            FullQuerry.append("DELETE FROM " + QuerryBuilder.PARENT_TABLES[atribute] + " WHERE " + atribute + " IS " + oldVal)
                        else:
                            FullQuerry.append("DELETE FROM " + QuerryBuilder.PARENT_TABLES[atribute] + " WHERE " + atribute + " = " + oldVal)

                    elif qualifier == table: #If atribute is in table
                        if oldAsNull:
                            where += QuerryBuilder.editSelected[atr] + " IS " + oldVal + " AND "
                        else:
                            where += QuerryBuilder.editSelected[atr] + " = " + oldVal + " AND "
                        editted = True

                if editted:
                    where = where[:-5] #Remove last " AND "
                    FullQuerry.append(querry + " " + where + "; ")

        return FullQuerry
    
    #Transform update to delete when primary key constraint fires
    def updateToDelete(self, query: str) -> str:
        return "DELETE FROM " + query.split()[1] + " " + query[query.find("WHERE"):]