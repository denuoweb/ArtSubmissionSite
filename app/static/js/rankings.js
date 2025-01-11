document.addEventListener("DOMContentLoaded", function () {
    console.info("Initializing rankings...");

    // Tab navigation logic
    initializeTabs();

    const rankingsList = document.getElementById("rankings-list");
    const rankInput = document.getElementById("rank-input");
    const rankingForm = document.querySelector("#ranking-form");
    const csrfToken = document.querySelector("input[name=csrf_token]").value; // Get CSRF token

    // Validate necessary elements exist
    if (!rankingsList || !rankInput || !rankingForm) {
        console.error("Required elements not found. Initialization aborted.");
        return;
    }

    // Initialize SortableJS for drag-and-drop functionality
    initializeSortable(rankingsList, rankInput, rankingForm, csrfToken);

    // Populate initial rankings on page load
    updateRankings(rankingsList, rankInput);

    // Handle final form submission
    handleFormSubmission(rankingForm, csrfToken, rankInput);
});

/**
 * Initialize Bootstrap tabs for navigation.
 */
function initializeTabs() {
    const triggerTabList = [].slice.call(document.querySelectorAll('#ballotTabs button'));
    triggerTabList.forEach(function (triggerEl) {
        const tabTrigger = new bootstrap.Tab(triggerEl);
        triggerEl.addEventListener('click', function (event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });
}

/**
 * Initialize SortableJS for the rankings list.
 * @param {HTMLElement} rankingsList
 * @param {HTMLInputElement} rankInput
 * @param {HTMLFormElement} rankingForm
 * @param {string} csrfToken
 */
function initializeSortable(rankingsList, rankInput, rankingForm, csrfToken) {
    Sortable.create(rankingsList, {
        animation: 150,
        onEnd: function () {
            updateRankings(rankingsList, rankInput); // Update rankings display and hidden input
            autoSaveRankings(rankInput, rankingForm, csrfToken); // Trigger auto-save on reorder
        },
    });
}

/**
 * Update the rank labels and hidden rank input field.
 * @param {HTMLElement} rankingsList
 * @param {HTMLInputElement} rankInput
 */
function updateRankings(rankingsList, rankInput) {
    const rankedItems = Array.from(rankingsList.querySelectorAll(".rank-item"));

    if (!rankedItems.length) {
        console.warn("No rank items found.");
        showNotification("No items to rank. Please refresh the page.", "warning");
        return;
    }

    const seenIds = new Set(); // Track seen IDs to avoid duplicates
    const rankings = rankedItems
        .map((item, index) => {
            const submissionId = item.getAttribute("data-id");

            // Debug log for troubleshooting
            console.debug(`Rank item: ${index + 1}, Submission ID: ${submissionId}`);

            // Skip duplicates
            if (seenIds.has(submissionId)) {
                console.warn(`Duplicate data-id found: ${submissionId}`);
                item.classList.add("duplicate-error"); // Highlight duplicates in UI
                return null;
            }
            seenIds.add(submissionId);

            // Ensure rank position element exists
            let rankPosition = item.querySelector(".rank-position");
            if (!rankPosition) {
                console.warn(`.rank-position element is missing for item with data-id: ${submissionId}. Adding dynamically.`);
                rankPosition = document.createElement("span");
                rankPosition.className = "rank-position";
                item.appendChild(rankPosition); // Dynamically append the missing element
            }

            // Update rank position display
            const rankSuffix = getRankSuffix(index + 1);
            rankPosition.textContent = `${index + 1}${rankSuffix} Place`;

            return submissionId; // Return valid submission ID
        })
        .filter((id) => id !== null); // Remove any null values

    // Populate the hidden input field with unique IDs
    rankInput.value = rankings.join(",");
    console.debug(`Rankings updated: ${rankInput.value}`);
}

/**
 * Auto-save rankings to the server.
 * @param {HTMLInputElement} rankInput
 * @param {HTMLFormElement} rankingForm
 * @param {string} csrfToken
 */
function autoSaveRankings(rankInput, rankingForm, csrfToken) {
    const rankedVotes = rankInput.value;

    console.debug("Auto-saving rankings:", rankedVotes);

    fetch(rankingForm.action, {
        method: "POST",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrfToken,
        },
        body: new URLSearchParams({ rank: rankedVotes }), // Send only the rank data
    })
        .then((response) => {
            if (response.ok) {
                console.info("Rankings saved automatically.");
                showNotification("Rankings saved automatically.", "success");
            } else {
                console.error("Failed to auto-save rankings:", response.status);
                showNotification("Failed to auto-save rankings.", "danger");
            }
        })
        .catch((error) => {
            console.error("Error during auto-save:", error);
            showNotification("An error occurred during auto-save.", "danger");
        });
}

/**
 * Handle final form submission.
 * @param {HTMLFormElement} rankingForm
 * @param {string} csrfToken
 * @param {HTMLInputElement} rankInput
 */
function handleFormSubmission(rankingForm, csrfToken, rankInput) {
    rankingForm.addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent default form submission behavior

        const formData = new FormData(rankingForm);
        console.debug("Submitting rankings form:", Array.from(formData.entries()));

        fetch(rankingForm.action, {
            method: "POST",
            body: new URLSearchParams(formData), // Convert formData to URL-encoded string
        })
            .then((response) => {
                if (response.redirected) {
                    console.info("Form submitted successfully. Redirecting...");
                    window.location.href = response.url;
                } else if (response.ok) {
                    console.info("Form submitted successfully.");
                    alert("Rankings submitted successfully! 🎉");
                } else {
                    console.error("Failed to submit rankings:", response.status);
                    alert("Failed to submit rankings. Please try again.");
                }
            })
            .catch((error) => {
                console.error("Error during form submission:", error);
                alert("An error occurred. Please try again.");
            });
    });
}

/**
 * Display a notification on the screen.
 * @param {string} message
 * @param {string} type
 */
function showNotification(message, type) {
    const notification = document.createElement("div");
    notification.className = `alert alert-${type} fixed-top`;
    notification.textContent = message;

    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000); // Remove after 3 seconds
}

/**
 * Helper function to get the rank suffix (e.g., 1st, 2nd, 3rd).
 * @param {number} rank
 * @returns {string}
 */
function getRankSuffix(rank) {
    if (rank === 1) return "st";
    if (rank === 2) return "nd";
    if (rank === 3) return "rd";
    return "th";
}
