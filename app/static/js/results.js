document.addEventListener("DOMContentLoaded", function () {
    // Initialize the tabs in the results page
    var triggerTabList = [].slice.call(document.querySelectorAll('#resultsTabs button'));
    triggerTabList.forEach(function (triggerEl) {
        var tabTrigger = new bootstrap.Tab(triggerEl);
        triggerEl.addEventListener('click', function (event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });
    
    // Clear Votes Button functionality
    document.getElementById("clearVotesButton").addEventListener("click", function () {
        if (!confirm("Are you sure you want to clear all votes? This action cannot be undone.")) {
            return; // Exit if the user cancels the confirmation
        }
    
        // Get the clear votes URL from the button's data attribute
        const clearVotesUrl = this.getAttribute("data-clear-votes-url");
        
        // Get the CSRF token from a hidden input (ensure your template renders one)
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    
        fetch(clearVotesUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken  // Include the CSRF token in the headers
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear the results table
                const resultsTable = document.getElementById("resultsTable");
                if (resultsTable) {
                    resultsTable.remove();
                }
    
                // Display "No results" message
                const noResultsMessage = document.getElementById("noResultsMessage");
                if (!noResultsMessage) {
                    const newMessage = document.createElement("p");
                    newMessage.id = "noResultsMessage";
                    newMessage.textContent = "No results are available yet. Judges need to submit their votes first.";
                    document.querySelector("body").appendChild(newMessage);
                }
    
                // Update voting status
                document.getElementById("votedJudgesList").innerHTML = "<li>No judges have voted yet.</li>";
                document.getElementById("notVotedJudgesList").innerHTML = "<li>All judges have not voted yet.</li>";
    
                alert("All judge votes have been cleared successfully!");
            } else if (data.error) {
                alert("Error: " + data.error);
            }
        })
        .catch(error => {
            console.error("Error clearing votes:", error);
            alert("An error occurred while clearing votes.");
        });
    });
    
    // Attach event listeners to all artwork-thumbnail links for opening the modal
    const artworkThumbnails = document.querySelectorAll(".artwork-thumbnail");
    artworkThumbnails.forEach(function(thumbnail) {
        thumbnail.addEventListener("click", function () {
            const artworkUrl = thumbnail.getAttribute("data-artwork-url");
            const name = thumbnail.getAttribute("data-name");
            const submissionId = thumbnail.getAttribute("data-id");
            const submissionType = thumbnail.getAttribute("data-type");
            // Call the modal-opening function from artwork_modal.js
            openArtworkModal(artworkUrl, name, submissionId, submissionType);
        });
    });
});
