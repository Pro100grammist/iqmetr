(function () {
    const metrics = document.getElementById("iq-result-metrics");
    const count = metrics ? parseInt(metrics.dataset.count || "30", 10) : 30;
    document.getElementById("progress-inner").style.width = "100%";
    document.getElementById(
        "progress-text"
    ).textContent = `${count} / ${count}`;
    document.getElementById("timer").textContent = "--:--";
})();
