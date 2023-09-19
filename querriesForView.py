class ViewSelector:
    def __init__(self):
        columns = "PRODUCT PRODUCT_ID DOI A_PARAMETER_MAX A_PARAMETER_MIN MIXING_METHOD SOURCE_MIX_TIME_MIN SOURCE_MIX_TIME_MAX METHOD GAS SYNTHESIS_TIME_MIN SYNTHESIS_TIME_MAX FEATURE CONTRIBUTOR COMMENTS synthesis_parameters synthesis_units synthesis_min_values synthesis_max_values meas_parameters meas_units meas_mins meas_maxes All_ingredients words countries internal_cipher url YEAR journal impact"
        self.allColumns = columns.split()
        print(self.allColumns)
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
    def querryForColComments(self, column): # querry to get comments to the collumn
        return "SELECT COLUMN_COMMENT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = \'heasm\' AND TABLE_NAME = \'MAIN_VIEW\' AND COLUMN_NAME = \'"+column+"\';"


VS = ViewSelector()
print(VS.getAllColumns())
print(VS.selectInfo(VS.getAllColumns()))
print(VS.querryTableInfo())
print(VS.querryForComments())
print(VS.querryForColComments('PRODUCT'))