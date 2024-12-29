document.addEventListener("DOMContentLoaded", function () {
    const rankingsList = document.getElementById("rankings-list");
    const rankInput = document.getElementById("rank-input");

    // Initialize SortableJS on the rankings list
    Sortable.create(rankingsList, {
        animation: 150,
        onEnd: function () {
            updateRankings();
        },
    });

    // Function to update the hidden rank input field
    function updateRankings() {
        const rankedItems = Array.from(rankingsList.querySelectorAll(".rank-item"));
        const rankings = rankedItems.map((item) => item.getAttribute("data-id"));
        rankInput.value = rankings.join(","); // Populate the hidden input field with the ranked IDs
    }

    // Call updateRankings initially to populate the input field on page load
    updateRankings();

    // Handle ranking form submission
    const rankingForm = document.querySelector("#ranking-form");

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
                    alert("Rankings submitted successfully!");
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
