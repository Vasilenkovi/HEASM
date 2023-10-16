class FilterString {

    static txtReLike = /(like)\s*["'](.*)["']/
    static compRe = /(=|<|>)\s*(.*)/
    static rangeRe = /\[([0-9\.]+)\s*,\s*([0-9\.]+)\]/

    static parseConstruction(str) {
        return str.split(";")
    }

    static parseString(str) {
        let parsed = str.match(FilterString.txtReLike)
        if (parsed == null) {
            let parsed = str.match(FilterString.compRe)
            if (parsed == null) {
                console.log("Invalid syntax")
                return null
            } else {
                if (parsed.length < 3) { //match, group 0, group 1
                    console.log("Invalid semantics")
                    return null
                } else {
                    return [parsed[1], parsed[2]]
                }
            }
        } else {
            if (parsed.length < 3) { //match, group 0, group 1
                console.log("Invalid semantics")
                return null
            } else {
                return [parsed[1], parsed[2]]
            }
        }
    }

    static checkRange(str) {
        let res = str.match(FilterString.rangeRe)
        if (res) {
            return [res[1], res[2]]
        } else {
            return null
        }
    }

    static txtCallback(rawString) {
        let parsered = FilterString.parseString(rawString.toLowerCase().trim())
        if (parsered[0] == "like") {
            return (elem) => { return elem.toLowerCase().includes(parsered[1]) }
        } else if (parsered[0] == "=") {
            return (elem) => { return elem.toLowerCase().trim() == parsered[1] }
        } else {
            console.log("Invalid semantics for txt column")
        }
    }

    static numCallback(rawString) {
        let parsered = FilterString.parseString(rawString.toLowerCase().trim())
        if (parsered[0] == "like") {
            console.log("Invalid semantics for num column, 'like'")
        } else if (parsered[0] == "=") {
            return (elem) => {
                let pElem = FilterString.checkRange(elem)
                if (pElem) {
                    return (Number(parsered[1]) >= Number(pElem[0])) && (Number(parsered[1]) <= Number(pElem[1]))
                } else {
                    return elem == Number(parsered[1])
                }
            }
        } else if (parsered[0] == ">") {
            return (elem) => {
                let pElem = FilterString.checkRange(elem)
                if (pElem) {
                    return (elem > Number(pElem[0])) && (elem > Number(pElem[1]))
                } else {
                    return elem > Number(parsered[1])
                }
            }
        } else if (parsered[0] == "<") {
            return (elem) => {
                let pElem = FilterString.checkRange(elem)
                if (pElem) {
                    return (elem < Number(pElem[0])) && (elem < Number(pElem[1]))
                } else {
                    return elem < Number(parsered[1])
                }
            }
        } else {
            console.log("Invalid semantics for num column, how did we even get here?")
        }
    }
}

function zip(a, b) {
    return a.map((k, i) => [k, b[i]])
}

function updateRowDataset(row, dict) {
    if ("doi" in dict) {
        row.dataset.doi = dict.doi
    }
    if ("journal" in dict) {
        row.dataset.journal = dict.journal
    }
    if ("productid" in dict) {
        row.dataset.productid = dict.productid
    }
    if ("year" in dict) {
        row.dataset.year = dict.year
    }
}

function logPrior(e) {
    e.target.dataset.prior = e.target.value
}

function logChanges(e) {
    if (e.target.dataset.prior != e.target.value) {
        rowInfo = e.target.parentNode.parentNode
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.value, e.target.dataset.prior, rowInfo.dataset.doi, rowInfo.dataset.journal, rowInfo.dataset.productid, rowInfo.dataset.year]

        for (key in IDcols) {
            if (IDcols[key] == e.target.dataset.cell) {
                changeDict = {}
                changeDict[key] = e.target.value
                updateRowDataset(rowInfo, changeDict)
            }
        }

        socket.emit("singleChanges", { data: changes });
    }
}

function logChangesSub(e) {
    if (e.target.dataset.prior != e.target.value) {
        rowInfo = e.target
        for (let i = 0; i < 8; i++) {
            rowInfo = rowInfo.parentNode
        }
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.dataset.subrow, e.target.dataset.subcell, e.target.value, e.target.dataset.prior, rowInfo.dataset.doi, rowInfo.dataset.journal, rowInfo.dataset.productid, rowInfo.dataset.year]

        for (key in IDcols) {
            if (IDcols[key] == e.target.dataset.cell) {
                changeDict = {}
                changeDict[key] = e.target.value
                updateRowDataset(rowInfo, changeDict)
            }
        }

        socket.emit("multipleChanges", { data: changes });
    }
}

function focusFull(e) {
    full = e.target.nextElementSibling
    full.focus()
    full.style.display = "block"
    e.target.style.display = "none"
}

function focusSmall(e) {
    parent = e.target.parentNode
    small = parent.previousElementSibling
    small.style.display = "block"
    parent.style.display = "none"
}

function applyFilter(e) {
    rawString = e.target.value
    if (rawString.trim()) {
        columnNumber = Number(e.target.dataset.column)
        columnType = colFormat[columnNumber]

        callbackFn = (elem) => {}
        callbackFnArray = []

        if (Array.isArray(columnType)) {

            preParsed = FilterString.parseConstruction(rawString)

            for (condition of zip(preParsed, columnType)) {
                if (!condition[0].trim()) {
                    callbackFnArray.push((elem) => { return true })
                    continue
                }

                if (condition[1] == "txt") {
                    callbackFnArray.push(FilterString.txtCallback(condition[0]))
                } else if (condition[1] == "num") {
                    callbackFnArray.push(FilterString.numCallback(condition[0]))
                } else {
                    console.log("unsupported column type")
                }
            }

            callbackFn = (elem) => {

                for (subRow of elem) {
                    acceptableSubRow = true

                    for (let i = 0; i < subRow.length; i++) {
                        acceptableSubRow = acceptableSubRow && callbackFnArray[i](subRow[i])
                    }

                    if (acceptableSubRow) {
                        return true
                    }
                }

                return false
            }

        } else if (columnType == "txt") {
            callbackFn = FilterString.txtCallback(rawString)
        } else if (columnType == "num") {
            callbackFn = FilterString.numCallback(rawString)
        } else {
            console.log("unsupported column type")
        }

        presentationRows = document.getElementsByClassName("hideableRow")
        for (let j = 0; j < fullTable.length; j++) {
            let t = callbackFn(fullTable[j][columnNumber])
            if (!t) {
                presentationRows[j].style.display = "none"
            }
        }

    } else {
        presentationRows = document.getElementsByClassName("hideableRow")

        for (row of presentationRows) {
            row.style.display = "table-row"
        }
    }
}

function addRowSub(e) {
    columnNumber = Number(e.target.colSpan)
    row = document.createElement("tr")
    row.classList.add("consumableRow")
    for (let i = 0; i < columnNumber; i++) {
        cell = document.createElement("td")
        cell.classList.add("bordered")

        inp = document.createElement("input")
        inp.classList.add("userInput")
        inp.type = "text"
        inp.value = ""
        inp.dataset.prior = ""
        inp.dataset.row = fullTable.length
        inp.dataset.cell = i
        inp.addEventListener("focus", logPrior)
        inp.addEventListener("blur", logChanges)
        cell.appendChild(inp)

        row.appendChild(cell)
    }

    rowTarget = e.target.parentNode
    table = e.target.parentNode.parentNode
    table.insertBefore(row, rowTarget)
}

function addRow(e) {
    columnNumber = Number(e.target.colSpan)
    row = document.createElement("tr")
    for (let i = 0; i < columnNumber; i++) {
        cell = document.createElement("td")
        cell.classList.add("bordered")

        if (Array.isArray(colFormat[i])) {
            mainDiv = document.createElement("div")
            mainDiv.classList.add("multipleValueSwitcher")

            smallDiv = document.createElement("div")
            smallDiv.classList.add("multipleValueDiv")
            smallDiv.textContent = "[Множественные значения]"
            smallDiv.addEventListener("click", focusFull)

            expandDiv = document.createElement("div")
            expandDiv.classList.add("expandIcon")
            smallDiv.appendChild(expandDiv)

            mainDiv.appendChild(smallDiv)

            bigDiv = document.createElement("div")
            bigDiv.classList.add("multipleValueDivFull")
            bigDiv.tabindex = ""

            minDiv = document.createElement("div")
            minDiv.classList.add("minimizer")
            minDiv.addEventListener("click", focusSmall)
            bigDiv.appendChild(minDiv)

            tableTag = document.createElement("table")
            tableTag.classList.add("bordered")
            tableTag.classList.add("multipleHolder")

            trPsa = document.createElement("tr")
            trPsa.classList.add("bordered")

            tdPsa = document.createElement("td")
            tdPsa.classList.add("bordered")
            tdPsa.classList.add("multipsa")
            tdPsa.colspan = colFormat[i].length
            tdPsa.textContent = "Добавить запись"

            trPsa.appendChild(tdPsa)
            tableTag.appendChild(trPsa)

            bigDiv.appendChild(tableTag)
            mainDiv.appendChild(bigDiv)

            cell.appendChild(mainDiv)

        } else {
            inp = document.createElement("input")
            inp.classList.add("userInput")
            inp.type = "text"
            inp.value = ""
            inp.dataset.prior = ""
            inp.dataset.row = fullTable.length
            inp.dataset.cell = i
            inp.addEventListener("focus", logPrior)
            inp.addEventListener("blur", logChanges)
            cell.appendChild(inp)
        }

        row.appendChild(cell)
    }

    table = e.target.parentNode.parentNode
    table.appendChild(row)
}

function commit1() {
    socket.emit("commit", { data: "changes" });
}

function addPopup() {
    bodyTag = document.getElementById("trueBody")
    bodyTag.style.opacity = 0.2

    bodyTag = document.getElementById("popup")
    bodyTag.style.display = "block"
}

function popupClose() {
    bodyTag = document.getElementById("trueBody")
    bodyTag.style.opacity = 1

    bodyTag = document.getElementById("popup")
    bodyTag.style.display = "none"

    rowsToDlt = document.getElementsByClassName("consumableRow")

    while (rowsToDlt.length > 0) {
        rowsToDlt[0].remove()
    }
}

function collectInputs(e) {
    addDict = {}

    mainArr = []
    main = document.getElementById("popupMain").children[0].children[1] //skip header
    for (td of main.children) {
        mainArr.push(td.children[0].value)
    }
    addDict["main"] = mainArr

    for (tableId of addExtra) {
        tableArr = []
        extraTableRows = document.getElementById(tableId[0]).children[0].children
        for (i = 1; i < extraTableRows.length - 1; i++) {
            newRow = []
            extraRowTd = extraTableRows[i].children
            for (td of extraRowTd) {
                newRow.push(td.children[0].value)
            }
            tableArr.push(newRow)
        }
        addDict[tableId[0]] = tableArr
    }

    socket.emit("addRows", addDict);
}

window.onload = () => {
    inputs = document.getElementsByClassName("userInput")

    for (tag of inputs) {
        tag.addEventListener("focus", logPrior)
        tag.addEventListener("blur", logChanges)
    }

    inputsSub = document.getElementsByClassName("userInputSub")

    for (tag of inputsSub) {
        tag.addEventListener("focus", logPrior)
        tag.addEventListener("blur", logChangesSub)
    }

    inputsMult = document.getElementsByClassName("multipleValueDiv")
    inputsMultFull = document.getElementsByClassName("minimizer")

    for (tag of inputsMult) {
        tag.addEventListener("click", focusFull)
    }

    for (tag of inputsMultFull) {
        tag.addEventListener("click", focusSmall)
    }

    inputsFilter = document.getElementsByClassName("userFilter")

    for (tag of inputsFilter) {
        tag.addEventListener("blur", applyFilter)
    }

    saveBtn = document.getElementById("saveButton")
    saveBtn.addEventListener("click", commit1)

    addRowBtn = document.getElementById("addRow")
    addRowBtn.addEventListener("click", addPopup)

    popupCloseBtn = document.getElementById("popupClose")
    popupCloseBtn.addEventListener("click", popupClose)

    popupAddBtn = document.getElementById("popupAdd")
    popupAddBtn.addEventListener("click", collectInputs)

    multipsaTag = document.getElementsByClassName("multipsa")
    for (tag of multipsaTag) {
        tag.addEventListener("click", addRowSub)
    }
}