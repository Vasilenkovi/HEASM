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