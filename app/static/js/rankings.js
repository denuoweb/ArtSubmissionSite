document.addEventListener("DOMContentLoaded", function () {
    console.info("Initializing ranking forms...");

    // --- Adult Ranking Form ---
    const rankingForm = document.getElementById("ranking-form");
    const rankingsList = document.getElementById("rankings-list");
    const rankInput = document.getElementById("rank-input");

    // --- Youth Ranking Form ---
    const youthRankingForm = document.getElementById("youth-ranking-form");
    const youthRankingsList = document.getElementById("youth-rankings-list");
    const youthRankInput = document.getElementById("youth-rank-input");

    // If present, init adult
    if (rankingForm && rankingsList && rankInput) {
        initSortable(rankingForm, rankingsList, rankInput);
    }

    // If present, init youth
    if (youthRankingForm && youthRankingsList && youthRankInput) {
        initSortable(youthRankingForm, youthRankingsList, youthRankInput);
    }
});

/**
 * Initialize SortableJS for a given form + list + hidden input.
 * @param {HTMLFormElement} formEl
 * @param {HTMLElement} listEl
 * @param {HTMLInputElement} rankInputEl
 */
function initSortable(formEl, listEl, rankInputEl) {
    const csrfToken = document.querySelector("input[name='csrf_token']")?.value || "";

    // Create Sortable instance
    Sortable.create(listEl, {
        animation: 150,
        onEnd: function () {
            updateRankings(listEl, rankInputEl);
            autoSaveRankings(formEl, rankInputEl, csrfToken);
        },
    });

    // Initial labeling
    updateRankings(listEl, rankInputEl);

    // Final form submission
    formEl.addEventListener("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(formEl);
        console.debug("Submitting final rankings form:", Array.from(formData.entries()));
        fetch(formEl.action, {
            method: "POST",
            body: new URLSearchParams(formData),
        })
            .then((response) => {
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    console.info("Rankings submitted successfully!");
                    alert("Rankings submitted successfully!");
                } else {
                    console.error("Failed to submit rankings:", response.status);
                    alert("Failed to submit rankings. Please try again.");
                }
            })
            .catch((error) => {
                console.error("Error during final form submission:", error);
                alert("An error occurred. Please try again.");
            });
    });
}

/**
 * Update the rank labels and hidden rank input field.
 * @param {HTMLElement} listEl - The container with .rank-item elements.
 * @param {HTMLInputElement} rankInputEl - The hidden input to store the comma-separated IDs.
 */
function updateRankings(listEl, rankInputEl) {
    const rankItems = Array.from(listEl.querySelectorAll(".rank-item"));
    if (!rankItems.length) {
        console.warn("No .rank-item found in listEl.");
        rankInputEl.value = "";
        return;
    }

    const seenIds = new Set();
    const rankedIds = [];

    rankItems.forEach((item, index) => {
        const submissionId = item.getAttribute("data-id");
        if (!submissionId) return;

        // If you genuinely have duplicates in the DOM, you can warn here:
        if (seenIds.has(submissionId)) {
            console.warn(`Duplicate data-id found: ${submissionId}. This item will be ignored in final ranking.`);
            return;
        }
        seenIds.add(submissionId);

        // Update label text, e.g., "1st Place", "2nd Place", etc.
        const rankPosEl = item.querySelector(".rank-position");
        if (rankPosEl) {
            const place = index + 1;
            rankPosEl.textContent = `${place}${getRankSuffix(place)} Place`;
        }
        // Collect submissionId for final input
        rankedIds.push(submissionId);
    });

    // Store comma-separated IDs
    rankInputEl.value = rankedIds.join(",");
    console.debug("Updated rank input:", rankInputEl.value);
}

/**
 * Auto-save rankings to the server (POST).
 * @param {HTMLFormElement} formEl
 * @param {HTMLInputElement} rankInputEl
 * @param {string} csrfToken
 */
function autoSaveRankings(formEl, rankInputEl, csrfToken) {
    if (!rankInputEl.value) {
        console.debug("No rank input to save.");
        return;
    }
    const formName = formEl.querySelector("input[name='form_name']")?.value || "";

    // We only need to send rank + form_name + csrf_token
    const payload = new URLSearchParams({
        rank: rankInputEl.value,
        form_name: formName,
        csrf_token: csrfToken,
    });

    fetch(formEl.action, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: payload.toString(),
    })
        .then((response) => {
            if (!response.ok) {
                console.warn("Auto-save failed with status:", response.status);
            } else {
                console.debug("Rankings auto-saved successfully.");
            }
        })
        .catch((error) => {
            console.error("Error during auto-save:", error);
        });
}

/**
 * Helper to get rank suffix (st, nd, rd, th).
 */
function getRankSuffix(rank) {
    if (rank % 100 >= 11 && rank % 100 <= 13) {
        return "th";
    }
    switch (rank % 10) {
        case 1:
            return "st";
        case 2:
            return "nd";
        case 3:
            return "rd";
        default:
            return "th";
    }
}
