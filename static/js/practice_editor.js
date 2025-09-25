(function () {
    const root = document.getElementById("practice-root");
    if (!root) return;

    const sUUID = root.dataset.session;
    const autosaveUrl = root.dataset.autosave;
    const evalUrl = root.dataset.eval;
    const taMot = document.getElementById("motivation");
    const taRes = document.getElementById("resolution");
    const timerEl = document.getElementById("timer");
    const wordsMot = document.getElementById("words-mot");
    const wordsRes = document.getElementById("words-res");

    function getCookie(name) {
        const m = document.cookie.match("(^|;)\\s*" + name + "=\\s*([^;]+)");
        return m ? m.pop() : "";
    }
    const csrftoken = getCookie("csrftoken");

    // ---- Заборона вставки/drag&drop (крім DEBUG) ----
    const isDebug = (document.body && document.body.dataset.debug === "true");
    const allowPaste = isDebug || (document.body && document.body.dataset.allowPaste === "true");
    if (!allowPaste) {
        const blockPaste = (e) => {
            e.preventDefault();
            pasteEvents++;
        };
        const blockKeys = (e) => {
            if ((e.ctrlKey || e.metaKey) && (e.key === "v" || e.key === "V")) {
                e.preventDefault();
                pasteEvents++;
            }
        };
        [taMot, taRes].forEach((el) => {
            el.addEventListener("paste", blockPaste);
            el.addEventListener("drop", blockPaste);
            el.addEventListener("beforeinput", (e) => {
                const t = e.inputType || "";
                if (t.startsWith("insertFromPaste") || t === "insertFromDrop") {
                    e.preventDefault();
                    pasteEvents++;
                }
            });
            el.addEventListener("keydown", blockKeys);
        });
    }

    // ---- Таймер ----
    let remaining = parseInt(root.dataset.remaining || "0", 10);
    function tick() {
        if (remaining <= 0) {
            // Автофініш: сабмітимо форму завершення
            document.getElementById("finish-form").submit();
            return;
        }
        const m = String(Math.floor(remaining / 60)).padStart(2, "0");
        const s = String(remaining % 60).padStart(2, "0");
        timerEl.textContent = `${m}:${s}`;
        remaining--;
        setTimeout(tick, 1000);
    }
    tick();

    // ---- Автозбереження ----
    let keypress = 0,
        pasteEvents = 0,
        t = null;
    function wc(s) {
        return (s.trim().match(/\S+/g) || []).length;
    }
    function updateCounts() {
        wordsMot.textContent = wc(taMot.value);
        wordsRes.textContent = wc(taRes.value);
    }
    function queueSave() {
        clearTimeout(t);
        t = setTimeout(doSave, 400);
    }
    function doSave() {
        fetch(autosaveUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken,
            },
            body: JSON.stringify({
                motivation_text: taMot.value,
                resolution_text: taRes.value,
                keypress_count: keypress,
                paste_event: pasteEvents,
            }),
        }).catch(() => {});
    }
    [taMot, taRes].forEach((el) => {
        el.addEventListener("input", () => {
            keypress++;
            updateCounts();
            queueSave();
        });
    });
    updateCounts();
    setInterval(doSave, 8000);
    window.addEventListener("beforeunload", doSave);

    // ---- Кнопка "Оцінити AI" ----
    const btnEval = document.getElementById("btn-eval");
    if (btnEval) {
        btnEval.addEventListener("click", () => {
            btnEval.disabled = true;
            fetch(evalUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrftoken },
            })
                .then((r) => r.json())
                .then((_) => location.reload())
                .catch((_) => {
                    btnEval.disabled = false;
                });
        });
    }
})();
