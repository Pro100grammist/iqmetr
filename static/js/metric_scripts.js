(function () {
    if (!("sendBeacon" in navigator)) return;

    let collectUrl = window.metricConfig && window.metricConfig.collectUrl;
    // Fallback if template tag didn't render or is missing
    if (!collectUrl || /\{\%|\%\}/.test(String(collectUrl))) {
        collectUrl = "/m/collect";
    }

    const body = JSON.stringify({
        lang: navigator.language || "",
        tz_offset: new Date().getTimezoneOffset(),
        screen_w: screen && screen.width ? screen.width : null,
        screen_h: screen && screen.height ? screen.height : null,
    });

    try {
        navigator.sendBeacon(
            collectUrl,
            new Blob([body], { type: "application/json" })
        );
    } catch (err) {
        if (window.console && typeof window.console.warn === "function") {
            console.warn("Failed to submit metrics beacon", err);
        }
    }
})();
