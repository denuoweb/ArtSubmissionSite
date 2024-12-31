document.addEventListener("DOMContentLoaded", function () {
    var triggerTabList = [].slice.call(document.querySelectorAll('#ballotTabs button'));
    triggerTabList.forEach(function (triggerEl) {
        var tabTrigger = new bootstrap.Tab(triggerEl);
        triggerEl.addEventListener('click', function (event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });
    
    const rankingsList = document.getElementById("rankings-list");
    const rankInput = document.getElementById("rank-input");
    const rankingForm = document.querySelector("#ranking-form");

    // Initialize SortableJS on the rankings list
    Sortable.create(rankingsList, {
        animation: 150,
        onEnd: function () {
            updateRankings(); // Update rankings display and hidden input
            autoSaveRankings(); // Trigger auto-save on reorder
        },
    });

    // Enable drag-and-drop ranking for youth submissions
    const youthRankingsList = document.getElementById("youth-rankings-list");
    const youthRankInput = document.getElementById("youth-rank-input");

    Sortable.create(youthRankingsList, {
        animation: 150,
        onEnd: function () {
            const rankedItems = Array.from(youthRankingsList.querySelectorAll(".rank-item"));
            const rankings = rankedItems.map((item) => item.getAttribute("data-id"));
            youthRankInput.value = rankings.join(",");
        },
    });

    // Function to update the rank labels and hidden rank input field
    function updateRankings() {
        const rankedItems = Array.from(rankingsList.querySelectorAll(".rank-item"));
        const seenIds = new Set(); // Track seen IDs to avoid duplicates
        const rankings = rankedItems
            .map((item, index) => {
                const submissionId = item.getAttribute("data-id");
    
                // Skip duplicates
                if (seenIds.has(submissionId)) {
                    console.warn(`Duplicate data-id found: ${submissionId}`);
                    return null; // Exclude this duplicate from the ranking
                }
                seenIds.add(submissionId);
    
                // Update rank position display
                const rankPosition = item.querySelector(".rank-position");
                const rankSuffix = getRankSuffix(index + 1);
                rankPosition.textContent = `${index + 1}${rankSuffix} Place`;
    
                return submissionId; // Return valid submission ID
            })
            .filter((id) => id !== null); // Remove any null values
    
        // Populate the hidden input field with unique IDs
        rankInput.value = rankings.join(",");
    }

    // Helper function to get the rank suffix (e.g., 1st, 2nd, 3rd)
    function getRankSuffix(rank) {
        if (rank === 1) return "st";
        if (rank === 2) return "nd";
        if (rank === 3) return "rd";
        return "th";
    }

    // Auto-save rankings to the server
    function autoSaveRankings() {
        const rankedVotes = rankInput.value; // Get updated rankings from the hidden input

        // Send AJAX request to save the updated rankings
        fetch(rankingForm.action, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            body: new URLSearchParams({ rank: rankedVotes }), // Send only the rank data
        })
            .then(response => {
                if (response.ok) {
                    showNotification("Rankings saved automatically.", "success");
                } else {
                    showNotification("Failed to auto-save rankings.", "danger");
                }
            })
            .catch(error => {
                console.error("Error during auto-save:", error);
                showNotification("An error occurred during auto-save.", "danger");
            });
    }

    // Display a notification
    function showNotification(message, type) {
        const notification = document.createElement("div");
        notification.className = `alert alert-${type} fixed-top`;
        notification.textContent = message;

        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000); // Remove after 3 seconds
    }

    // Call updateRankings initially to populate the input field and rank positions on page load
    updateRankings();

    // Handle final ranking form submission
    rankingForm.addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent default form submission behavior

        const formData = new FormData(rankingForm);

        fetch(rankingForm.action, {
            method: "POST",
            body: new URLSearchParams(formData), // Convert formData to URL-encoded string
        })
            .then(response => {
                if (response.redirected) {
                    // Redirect to the response URL if redirected by Flask
                    window.location.href = response.url;
                } else if (response.ok) {
                    alert("Rankings submitted successfully! 🎉");
                } else {
                    alert("Failed to submit rankings. Please try again.");
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("An error occurred. Please try again.");
            });
    });
});
