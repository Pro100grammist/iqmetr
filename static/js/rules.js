// Правила: прогрес 0/30, таймер = з контексту (через data-duration)
const durationEl = document.getElementById("iq-rules");
const seconds = durationEl
    ? parseInt(durationEl.dataset.duration || "1200", 10)
    : 1200;
const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
const ss = String(seconds % 60).padStart(2, "0");

document.getElementById("progress-inner").style.width = "0%";
document.getElementById("progress-text").textContent = "0 / 30";
document.getElementById("timer").textContent = `${mm}:${ss}`;
