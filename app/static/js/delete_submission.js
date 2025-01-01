// Function to handle deleting a submission
function deleteSubmission(submissionId) {
    if (!confirm("Are you sure you want to delete this submission?")) {
        return; // Exit if user cancels confirmation
    }

    const csrfToken = document.querySelector('input[name="csrf_token"]').value; // CSRF token

    fetch(`judges/ballot/delete/${submissionId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken, // Include CSRF token in the headers
        },
    })
        .then((response) => {
            if (response.ok) {
                // Remove the submission's <li> element from the DOM
                const listItem = document.querySelector(`li[data-id="${submissionId}"]`);
                if (listItem) {
                    listItem.remove();
                }
                alert("Submission deleted successfully!");
            } else if (response.status === 403) {
                alert("Unauthorized: Admin privileges are required to delete this submission.");
            } else {
                alert("Failed to delete the submission.");
            }
        })
        .catch((error) => {
            console.error("Error:", error);
            alert("An error occurred while trying to delete the submission.");
        });
}

document.addEventListener("DOMContentLoaded", function() {
    // Select all delete buttons
    const deleteButtons = document.querySelectorAll(".delete-button");
  
    deleteButtons.forEach((button) => {
      button.addEventListener("click", function(event) {
        // Extract submission ID from data attribute
        const submissionId = event.target.dataset.id;
        
        // Call your existing deleteSubmission function
        deleteSubmission(submissionId);
      });
    });
  });
  