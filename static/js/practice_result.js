(function () {
    // дістаємо URL метрик із HTML (data-атрибут у шаблоні result.html)
    const ep = document.getElementById("metrics-endpoints");
    const METRICS_URL = ep?.dataset?.collectUrl || null;

    // CSRF має бути на початку, щоб було доступно і метрикам, і іншим запитам
    function getCookie(name) {
        const m = document.cookie.match("(^|;)\\s*" + name + "=\\s*([^;]+)");
        return m ? m.pop() : "";
    }
    const csrftoken = getCookie("csrftoken");

    // Handle "Evaluate now" button if present
    const btn = document.getElementById("btn-eval");
    if (btn) {
        btn.addEventListener("click", () => {
            const url = btn.dataset.url;
            btn.disabled = true;
            fetch(url, {
                method: "POST",
                headers: { "X-CSRFToken": csrftoken },
            })
                .then((r) => r.json())
                .then(() => location.reload())
                .catch(() => {
                    btn.disabled = false;
                });
        });
    }

    // NEW: відправити факт перегляду результату (опційно)
    const root = document.getElementById("result-root");
    const sessionUUID = root?.dataset?.session || null;
    if (METRICS_URL && sessionUUID) {
        // зробимо без await, “в фоновому режимі”
        try {
            fetch(METRICS_URL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrftoken,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    event: "practice_result_view",
                    session_uuid: sessionUUID,
                }),
            });
        } catch (e) {
            /* no-op */
        }
    }

    // Fix duration rendering (use precise elapsed seconds instead of timesince rounding to 0m)
    if (root && root.dataset.elapsed) {
        const sec = parseInt(root.dataset.elapsed, 10);
        if (!isNaN(sec)) {
            const h = Math.floor(sec / 3600);
            const m = Math.floor((sec % 3600) / 60);
            const s = sec % 60;
            const text =
                h > 0
                    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(
                          2,
                          "0"
                      )}`
                    : `${m}:${String(s).padStart(2, "0")}`;
            const grid = document.querySelector(".meta-grid");
            if (grid) {
                const valCell = grid.querySelector(
                    ":scope > div:nth-child(10)"
                );
                if (valCell) valCell.textContent = text;
            }
        }
    }

    // Print / Save-to-PDF for the final document
    const printBtn = document.getElementById("btn-print");
    if (printBtn) {
        printBtn.addEventListener("click", () => {
            const docEl = document.querySelector(".prose");
            if (!docEl) return;
            const win = window.open("", "_blank");
            if (!win) return;
            win.document
                .write(`<!doctype html><html><head><meta charset="utf-8"><title>Document</title>
                <style>
                    @page { margin: 20mm; }
                    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.5; font-size: 12pt; color: #000; }
                    .doc { max-width: 210mm; margin: 0 auto; }
                    .doc div[style*="text-align:center"] { text-align: center; }
                </style>
            </head><body><div class="doc">${docEl.innerHTML}</div></body></html>`);
            win.document.close();
            win.focus();
            setTimeout(() => {
                win.print();
                win.close();
            }, 200);
        });
    }
})();
