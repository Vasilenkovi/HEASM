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
            console.log(parsered[1])
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

function logPrior(e) {
    e.target.dataset.prior = e.target.value
}

function logChanges(e) {
    if (e.target.dataset.prior != e.target.value) {
        rowInfo = e.target.parentNode.parentNode
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.value, e.target.dataset.prior, rowInfo.dataset.doi, rowInfo.dataset.journal]
        console.log(changes)
        socket.emit("singleChanges", { data: changes });
    }
}

function logChangesSub(e) {
    if (e.target.dataset.prior != e.target.value) {
        rowInfo = e.target
        for (let i = 0; i < 8; i++) {
            rowInfo = rowInfo.parentNode
        }
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.dataset.subrow, e.target.dataset.subcell, e.target.value, e.target.dataset.prior, rowInfo.dataset.doi, rowInfo.dataset.journal]
        console.log(changes)
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

        if (columnType == "txt") {
            callbackFn = FilterString.txtCallback(rawString)
        } else if (columnType == "num") {
            callbackFn = FilterString.numCallback(rawString)
        } else if (Array.isArray(columnType)) {

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

        } else {
            console.log("unsupported column type")
        }

        console.log(callbackFnArray)
        presentationRows = document.getElementsByClassName("hideableRow")
        for (let j = 0; j < fullTable.length; j++) {
            console.log(j)
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
}