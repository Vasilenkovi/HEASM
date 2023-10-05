class FilterString {

    static txtReLike = /(like)\s*["'](.*)["']/
    static compRe = /(=|<|>)\s*([\w]*)/

    static parseConstruction(str) {
        return str.split(";")
    }

    static parseString(str) {
        parsed = str.match(FilterString.txtReLike)
        if (parsed == null) {
            parsed = str.match(FilterString.compRe)
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

    static txtCallback(rawString) {
        parsered = FilterString.parseString(rawString.toLowerCase())
        if (parsered[0] == "like") {
            return (elem) => { return elem.includes(parsered[1]) }
        } else if (parsered[0] == "=") {
            return (elem) => { return elem == parsered[1] }
        } else {
            console.log("Invalid semantics for txt column")
        }
    }

    static numCallback(rawString) {
        parsered = FilterString.parseString(rawString.toLowerCase())
        if (parsered[0] == "like") {
            console.log("Invalid semantics for num column, 'like'")
        } else if (parsered[0] == "=") {
            return (elem) => { return elem = Number(parsered[1]) }
        } else if (parsered[0] == ">") {
            return (elem) => { return elem > Number(parsered[1]) }
        } else if (parsered[0] == "<") {
            return (elem) => { return elem < Number(parsered[1]) }
        } else {
            console.log("Invalid semantics for num column, how did we even get here?")
        }
    }
}

function zip(a, b) {
    return a.map((k, i) => [k, b[i]])
}

function logPrior(e) {
    e.target.dataset.prior = e.target.value
}

function logChanges(e) {
    if (e.target.dataset.prior != e.target.value) {
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.value]
        console.log(changes)
    }
}

function logChangesSub(e) {
    if (e.target.dataset.prior != e.target.value) {
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.dataset.subrow, e.target.dataset.subcell, e.target.value]
        console.log(changes)
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
        columnType = JSON.parse(e.target.dataset.columnType)

        callbackFn = (elem) => {}

        if (columnType == "txt") {
            callbackFn = FilterString.txtCallback(rawString)
        } else if (columnType == "num") {
            callbackFn = FilterString.numCallback(rawString)
        } else if (Array.isArray(columnType)) {

            preParsed = FilterString.parseConstruction(rawString)
            callbackFnArray = []

            for (condition in zip(preParsed, columnType)) {

                if (!condition[0].trim()) {
                    callbackFnArray.push((elem) => { return True })
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

                for (subRow in elem) {
                    acceptableSubRow = true

                    for (i = 0; i < subRow.length; i++) {
                        acceptableSubRow &= callbackFnArray[i](subRow[i])
                    }

                    if (acceptableSubRow) {
                        return true
                    }
                }

                return false
            }
        } else {
            console.log("unsupported column type")
        }

        presentationRows = document.getElementsByClassName("hideableRow")
        for (i = 0; i < fullTable.length; i++) {
            if (callbackFn(fullTable[i])) {
                presentationRows[1].style.display = "none"
            } else {
                presentationRows[1].style.display = "initial"
            }
        }
    } else {
        presentationRows = document.getElementsByClassName("hideableRow")

        for (row in presentationRows) {
            row.style.display = "initial"
        }
    }
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
}