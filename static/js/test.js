(function () {
    const root = document.getElementById("iq-test");
    if (!root) return;

    const form = document.getElementById("test-form");
    const timerEl = document.getElementById("timer");
    const barInner = document.getElementById("progress-inner");
    const barText = document.getElementById("progress-text");

    let remaining = parseInt(root.dataset.remaining || "0", 10);
    const total = parseInt(root.dataset.total || "30", 10);
    const autosaveUrl = root.dataset.autosave;

    function getCookie(name) {
        const m = document.cookie.match(
            "(^|;)\\s*" + name + "\\s*=\\s*([^;]+)"
        );
        return m ? m.pop() : "";
    }
    const csrftoken = getCookie("csrftoken");

    function tick() {
        if (remaining <= 0) {
            const fin = document.createElement("input");
            fin.type = "hidden";
            fin.name = "finish_now";
            fin.value = "1";
            form.appendChild(fin);
            form.submit();
            return;
        }
        const m = String(Math.floor(remaining / 60)).padStart(2, "0");
        const s = String(remaining % 60).padStart(2, "0");
        timerEl.textContent = `${m}:${s}`;
        remaining--;
        setTimeout(tick, 1000);
    }
    tick();

    function updateProgress() {
        const answered = new Set();
        document.querySelectorAll(".question").forEach((q) => {
            const qid = q.getAttribute("data-qid");
            if (q.querySelector("input[type=radio]:checked")) answered.add(qid);
        });
        const done = answered.size;
        const pct = Math.round((done / total) * 100);
        barInner.style.width = pct + "%";
        barText.textContent = `${done} / ${total}`;
    }

    let t = null;
    function autosave(qid, aid) {
        if (!autosaveUrl) return;
        clearTimeout(t);
        t = setTimeout(() => {
            fetch(autosaveUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({
                    question_id: Number(qid),
                    answer_id: Number(aid),
                }),
            })
                .then((r) => (r.ok ? r.json() : null))
                .then((data) => {
                    if (data && data.ok) updateProgress();
                })
                .catch(() => {});
        }, 200);
    }

    document.querySelectorAll("input[type=radio]").forEach((i) => {
        i.addEventListener("change", (e) => {
            updateProgress();
            const q = e.target.closest(".question");
            const qid = q.getAttribute("data-qid");
            const aid = e.target.value;
            autosave(qid, aid);
        });
    });
    updateProgress();

    window.addEventListener("beforeunload", function (e) {
        e.preventDefault();
        e.returnValue = "";
    });
})();
