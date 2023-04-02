from tkinter import *
import mysql.connector
import VerticalFrame #native tkinter scrollable frame. https://stackoverflow.com/questions/16188420/tkinter-scrollbar-for-frame

#class-entry point of an app
class App():

    def __init__(self):
        root = Tk()
        root.geometry("1980x720") #Window size (DPI unaware!)
        lf = LoginFrame(root, self) #LoginFrame takes app root to use in child frames, self is passed to access MySQL connection in child frames
        lf.pack()
        root.mainloop()
    
    #Static method for changing between app screens, both frames should have "setBkg()" method defined to change backgrounds between frames
    def switchFrame(source: Frame, target: Frame) -> None:
        source.pack_forget()
        source.bkg_label.place_forget()
        target.pack()
        target.setBkg()

    #Connecting to MySQL server and storing the connection in this App instance for other querries
    #Returns True if connection was successful, otherwise false
    def connect(self, user: str, password: str) -> bool:
        try:
            self.connection = mysql.connector.connect(user=user, password=password, host=App.HOST, port=App.PORT, database=App.DATABASE)
            self.cursor = self.connection.cursor()
            self.LookUp = self.execute("SELECT DISTINCT column_name, table_name FROM information_schema.columns WHERE table_schema = DATABASE() ORDER BY column_name;") #LookUp table is generated once on connection and used to quickly disambiguate between columns of different tables with the same names
            self.columnComments = self.execute("SELECT DISTINCT column_name, column_comment FROM information_schema.columns WHERE table_schema = DATABASE() ORDER BY column_comment;") #Retrieving comments to columns to present the user
            return True
        except:
            return False

    #Executes querries on App instance with prior successful conection
    def execute(self, query: str) -> list:
        if self.cursor != None:
            self.cursor.reset()
            self.cursor.execute(query)
            return self.cursor.fetchall() #Retrieving all results from cursor

    #Static member constants
    HOST = '127.0.0.1'
    PORT = 3306
    DATABASE = 'heasm'

class LoginFrame(Frame):

    def __onClick(self) -> None:
        #Disabled for development only
        #if App.connect(self.loginEntry.get(), self.passwordEntry.get()):
        #    App.switchFrame(self, self.optionsFrame)
        if self.cursor.connect('Gigachad', 'MegaBasedYarik1984'):
            App.switchFrame(self, self.optionsFrame)

    #cursor - reference to App instance to call querries on
    def __init__(self, root: Tk, cursor: App):
        self.cursor = cursor
        self.optionsFrame = OptionsFrame(root, cursor) #cursor passed to child frames

        self.bkg = PhotoImage(file = "bkg.png")
        self.bkg_label = Label(root, image = self.bkg)
        self.bkg_label.place(x = 0, y = 0)

        Frame.__init__(self, root)

        self.loginEntry = Entry(self)
        self.passwordEntry = Entry(self)
        self.enterButton = Button(self, text=u"➡", command=self.__onClick)

        self.loginEntry.grid(row = 0, column = 0)
        self.passwordEntry.grid(row = 1, column = 0)
        self.enterButton.grid(row = 1, column = 1)

        self.loginEntry.insert(0, "login") #User hints
        self.passwordEntry.insert(0, "password") #User hints

    #Public method to call during frame change
    def setBkg(self) -> None:
        self.bkg_label.place(x = 0, y = 0)

class OptionsFrame(Frame):

    def __onClickSelect(self) -> None:
        App.switchFrame(self, self.selectFrame)

    #cursor - reference to App instance to call querries on
    def __init__(self, root: Tk, cursor: App):
        self.selectFrame = SelectFrame(root, self, cursor)

        self.bkg = PhotoImage(file = "bkg.png")
        self.bkg_label = Label(root, image = self.bkg)
        self.bkg_label.place(x = 0, y = 0)

        Frame.__init__(self, root)

        self.selectButton = Button(self, text=u"Просмотр", command=self.__onClickSelect)
        self.editButton = Button(self, text=u"Редактирование")
        self.addButton = Button(self, text=u"Добавление")

        self.selectButton.grid(row = 0, column = 0)
        self.editButton.grid(row = 1, column = 0)
        self.addButton.grid(row = 2, column = 0)
    
    #Public method to call during frame change
    def setBkg(self) -> None:
        self.bkg_label.place(x = 0, y = 0)

class SelectFrame(Frame):

    #Called after executing the querry to display results. Currently text only
    def __display(self) -> None:
        self.displayText.delete(1.0,END) #clear previous
        for e in self.lastResult: #for every entry
            for a in e: #for every attribute
                self.displayText.insert(END, a+"; ") #add separator for readablility
            self.displayText.insert(END, "\n") #break lines between entries

    def __onClickGo(self) -> None:
        self.prefixLookUp = self.__lookUp() #Obtain reference to table lookup
        querry = "SELECT " #base of querry
        select = [] #all columns to select
        where = [] #all columns to include in "WHERE" statement
        whereSymbol = [] #all "WHERE" comparison operators
        whereCondition = [] #all "WHERE" conditions

        for f in self.filters: #for every created filter
            if f.checkBoxSelectVar.get():
                select.append(self.prefixLookUp[f.colName][0] + "." + f.colName) #if checked as "SELECT" add to select with table disambiguation from lookup
            if f.checkboxWhereVar.get():
                where.append(self.prefixLookUp[f.colName][0] + "." + f.colName) #if checked as "WHERE" add to where with table disambiguation from lookup
                whereSymbol.append(f.whereOptionVar.get())
                whereCondition.append(f.whereCondition())
        
        querry += ",".join(select)
        querry += """ FROM synthesis_product INNER JOIN synthesis_parameter ON synthesis_product.PRODUCT_ID = synthesis_parameter.PRODUCT_ID
        INNER JOIN ingredients ON synthesis_product.PRODUCT_ID = ingredients.PRODUCT_ID
        INNER JOIN measurements ON synthesis_product.PRODUCT_ID = measurements.PRODUCT_ID
        INNER JOIN bibliography ON synthesis_product.DOI = bibliography.DOI
        INNER JOIN source ON bibliography.JOURNAL = source.JOURNAL
        INNER JOIN key_word ON bibliography.DOI = key_word.DOI """.replace("\n", " ")

        if len(where) > 0: #if any filters were checked for "WHERE"
            querry += "WHERE "
            for w in range(len(where)):
                try:
                    querry += where[w] + whereSymbol[w] + str(float(whereCondition[w])) + " AND " #if a number was supplied as condition, comparison operators have meaning and are allowed
                except:
                    querry += where[w] + "='" + whereCondition[w] + "'" + " AND " #if a string was supplied as condition, comparison operators, aside from '=', have meaning and are defaulted to '='. Also quotation marks are provided
            querry = querry[:-5] + "\n" #last boolean logic operator is removed, because it has no right hand side condition. Currently only 'AND' is supported

        if self.filters[0].radioVar.get() == 1:
            querry += "ORDER BY " + self.filters[0].colName + " ASC" #if ascending sorting was chosen 
        elif self.filters[0].radioVar.get() == 2:
            querry += "ORDER BY " + self.filters[0].colName + " DESC" #if descending sorting was chosen 

        self.lastResult = self.cursor.execute(querry) #store the result for processing
        self.__display() #process the result

    def __onClickAdd(self) -> None:
        self.colCom = self.cursor.columnComments #obtain column comments reference to provide to user

        filterOptions = Toplevel(self.root) #created a new dialogue for filter selection
        filterOptions.grab_set() #make new dialogue blocking
        listbox = Listbox(filterOptions, selectmode='multiple')

        for row in self.colCom: #for every column
            listbox.insert(END, row[1].decode('utf-8', 'ignore')) #fill listbox with column comments for user

        listbox.pack()

        def __onClickApply() -> None:
            ids = listbox.curselection()

            for i in ids: #for every selected column
                if i not in self.chosen:
                    self.chosen.append(i) #keep track of already selected columns to avoid duplicates
                    self.filters.append(Filter(self.filterFrame.interior, self, len(self.filters), self.colCom[i][0], self.colCom[i][1].decode('utf-8', 'ignore'))) #Filter is additionally provided with its id in filters list for easy removal

            filterOptions.grab_release() #make dialogue non-blocking
            filterOptions.destroy()

        acceptButton = Button(filterOptions, text=u"Добавить", command=__onClickApply)
        acceptButton.pack()
        
    def __onClickBack(self) -> None:
        self.chosen.clear()

        for i in self.filters: #clear all filters to start over
            i.destroy()
        self.filters.clear()
        App.switchFrame(self, self.back)

    #forms lookup dictionary from App instance's list. Every column becomes associated with one or more tables for disambiguation purposes
    def __lookUp(self) -> dict:
        res = {}
        colTab = self.cursor.LookUp
        for i in range(len(colTab)): #for every column
            if colTab[i][0] not in res: 
                res[colTab[i][0]] = [] #create list of tables for column if there is none
            res[colTab[i][0]].append(colTab[i][1]) #append table to list of the column
        return res

    #cursor - reference to App instance to call querries on
    def __init__(self, root: Tk, back: Frame, cursor: App):
        #member variables
        self.cursor = cursor
        self.back = back
        self.root = root

        self.colCom = []
        self.prefixLookUp = {}
        self.lastResult = []

        self.chosen = [] #keep track of all chosen filters
        self.filters = [] #kepp refernces to physical frames

        self.bkg = PhotoImage(file = "bkg.png")
        self.bkg_label = Label(root, image = self.bkg)
        self.bkg_label.place(x = 0, y = 0)

        Frame.__init__(self, root)

        self.filterFrame = VerticalFrame.VerticalScrolledFrame(self)
        self.resultFrame = Frame(self)
        self.displayText = Text(self.resultFrame) #text widget to show results
        self.addButton = Button(self, text=u"Добавить", command=self.__onClickAdd)
        self.backButton = Button(self, text=u"Назад", command=self.__onClickBack)
        self.goButton = Button(self, text=u"Выполнить", command=self.__onClickGo)

        self.filterFrame.grid(row = 0, column = 0)
        self.resultFrame.grid(row = 0, column = 1)
        self.addButton.grid(row = 1, column = 0)
        self.backButton.grid(row = 1, column = 1)
        self.goButton.grid(row = 2, column = 1)
        self.displayText.pack()

    #Public method to call during frame change
    def setBkg(self) -> None:
        self.bkg_label.place(x = 0, y = 0)

    #Called from filter to properly destroy self and exclude itself from registry
    def freeUpId(self, x: int) -> None:
        if x < len(self.chosen):
            del self.chosen[x]
            del self.filters[x]
    
class Filter(Frame):

    def __onClick(self) -> None:
        self.selectFrame.freeUpId(self.frameId)
        self.destroy()

    #selectFrame - refernce to SelectFrame for proper deletion
    #frameId - Id in a frame list of SelectFrame instance. Used for proper deletion
    #colName - real name of associated column in DB for querries
    #displayName - name to display to user
    def __init__(self, root: Frame, selectFrame: SelectFrame, frameId: int, colName: str, displayName: str):
        Frame.__init__(self, root, width=60)
        #member variables
        self.selectFrame = selectFrame

        self.frameId = frameId
        self.colName = colName
        self.checkBoxSelectVar = BooleanVar()
        self.checkboxWhereVar = BooleanVar()
        self.radioVar = IntVar()
        self.whereOptionVar = StringVar()

        self.selectCheck = Checkbutton(self, text=u"Показать", variable=self.checkBoxSelectVar) #use filter in "SELECT" or not
        self.name = Entry(self, width=10)
        self.name.insert(END, displayName)
        self.name.config(state=DISABLED)
        self.closeButton = Button(self, text="x", command=self.__onClick)
        self.noOrder = Radiobutton(self, text="Не сортировать", variable=self.radioVar, value=0)
        self.asc = Radiobutton(self, text="По возрастанию", variable=self.radioVar, value=1)
        self.desc = Radiobutton(self, text="По убыванию", variable=self.radioVar, value=2)
        self.whereCheck = Checkbutton(self, text=u"Отобрать", variable=self.checkboxWhereVar) #use filter in "WHERE" or not
        self.condition = OptionMenu(self, self.whereOptionVar, *Filter.conditionOptions) #choice of comparison operator
        self.whereEntry = Entry(self, width=10)

        self.selectCheck.grid(row = 0, column = 0)
        self.name.grid(row = 0, column = 1)
        self.closeButton.grid(row = 0, column = 2)
        self.noOrder.grid(row = 1, column = 0)
        self.asc.grid(row = 1, column = 1)
        self.desc.grid(row = 1, column = 2)
        self.whereCheck.grid(row = 2, column = 0)
        self.condition.grid(row = 2, column = 1)
        self.whereEntry.grid(row = 2, column = 2)

        self.pack()
    
    #public getter for condition for "WHERE" clause. Because calling get() method on variable instead of simply reading from it is always forgotten 
    def whereCondition(self) -> str:
        return self.whereEntry.get()

    #member constants
    conditionOptions = ["=", ">", "<", ">=", "<="]

if __name__ == '__main__': #if run as standalone file, not module
    app = App()