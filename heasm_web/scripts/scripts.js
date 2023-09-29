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
        changes = [e.target.dataset.row, e.target.dataset.cell, e.target.dataset.subRow, e.target.dataset.subCell, e.target.value]
        console.log(changes)
    }
}

function focusFull(e) {
    full = e.target.nextSibling()
    full.focus()
    full.style.display = "block"
    e.target.style.display = "none"
}

function focusSmall(e) {
    small = e.target.previousSibling()
    small.style.display = "block"
    e.target.style.display = "none"
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

    inputsMult = document.getElementsByClassName("multipleValueSwitcher")

    for (tag of inputsMult) {
        tag.childNodes[0].addEventListener("focus", logPrior)
        tag.childNodes[1].addEventListener("focus", logPrior)
    }
}