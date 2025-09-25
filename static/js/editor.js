(function () {
    const body = document.body;
    if (!body) return;

    const debugEnabled = body.dataset.debug === "true";
    if (!debugEnabled) return;

    const unlock = (event) => {
        // Allow the browser to handle the paste/drop normally.
        event.stopImmediatePropagation();
    };

    document.addEventListener("paste", unlock, true);
    document.addEventListener("drop", unlock, true);
})();
