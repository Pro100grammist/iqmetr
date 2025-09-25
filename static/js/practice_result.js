(function () {
    // Handle "Evaluate now" button if present
    const btn = document.getElementById("btn-eval");
    if (btn) {
        function getCookie(name) {
            const m = document.cookie.match("(^|;)\\s*" + name + "=\\s*([^;]+)");
            return m ? m.pop() : "";
        }
        const csrftoken = getCookie("csrftoken");

        btn.addEventListener("click", () => {
            const url = btn.dataset.url;
            btn.disabled = true;
            fetch(url, { method: "POST", headers: { "X-CSRFToken": csrftoken } })
                .then((r) => r.json())
                .then(() => location.reload())
                .catch(() => {
                    btn.disabled = false;
                });
        });
    }

    // Fix duration rendering (use precise elapsed seconds instead of timesince rounding to 0m)
    const root = document.getElementById("result-root");
    if (root && root.dataset.elapsed) {
        const sec = parseInt(root.dataset.elapsed, 10);
        if (!isNaN(sec)) {
            const h = Math.floor(sec / 3600);
            const m = Math.floor((sec % 3600) / 60);
            const s = sec % 60;
            const text = h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
            const grid = document.querySelector('.meta-grid');
            if (grid) {
                const valCell = grid.querySelector(':scope > div:nth-child(10)');
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
            win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Document</title>
                <style>
                    @page { margin: 20mm; }
                    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.5; font-size: 12pt; color: #000; }
                    .doc { max-width: 210mm; margin: 0 auto; }
                    .doc div[style*="text-align:center"] { text-align: center; }
                </style>
            </head><body><div class="doc">${docEl.innerHTML}</div></body></html>`);
            win.document.close();
            win.focus();
            setTimeout(() => { win.print(); win.close(); }, 200);
        });
    }
})();
