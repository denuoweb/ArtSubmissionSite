// Function to handle deleting an artist (adult) submission asynchronously.
function deleteSubmission(submissionId) {
    if (!confirm("Are you sure you want to delete this submission?")) {
        return;
    }

    // Retrieve the CSRF token value from a hidden input element.
    const csrfTokenElement = document.querySelector('input[name="csrf_token"]');
    if (!csrfTokenElement) {
        console.error("CSRF token element not found.");
        return;
    }
    const csrfTokenValue = csrfTokenElement.value;

    // Construct the URL for deletion by including the "artist" submission type.
    const deleteUrl = `${typeof basePath !== "undefined" ? basePath : ""}/judges/ballot/delete/artist/${submissionId}`;

    // Send an asynchronous POST request to the deletion endpoint.
    fetch(deleteUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfTokenValue,  // Use the value property here.
        },
    })
    .then((response) => {
        if (response.ok) {
            // Remove the corresponding .rank-item element from the DOM.
            const submissionElement = document.querySelector(`.rank-item[data-id="${submissionId}"]`);
            if (submissionElement) {
                submissionElement.remove();
            }
            alert("Submission deleted successfully!");
        } else if (response.status === 403) {
            alert("Unauthorized: Admin privileges are required to delete this submission.");
        } else {
            alert("Failed to delete the submission.");
        }
    })
    .catch((error) => {
        console.error("Error during deletion:", error);
        alert("An error occurred while trying to delete the submission.");
    });
}

// Function to handle deleting a youth submission asynchronously.
function deleteYouthSubmission(submissionId) {
    if (!confirm("Are you sure you want to delete this submission?")) {
        return;
    }

    // Retrieve the CSRF token value from a hidden input element.
    const csrfTokenElement = document.querySelector('input[name="csrf_token"]');
    if (!csrfTokenElement) {
        console.error("CSRF token element not found.");
        return;
    }
    const csrfTokenValue = csrfTokenElement.value;

    // Construct the URL for deletion with 'youth' included in the path.
    const deleteUrl = `/judges/ballot/delete/youth/${submissionId}`;

    // Send an asynchronous POST request to the deletion endpoint.
    fetch(deleteUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfTokenValue,  // Use the value property here.
        },
    })
    .then(response => {
        if (response.ok) {
            const submissionElement = document.querySelector(`.rank-item[data-id="${submissionId}"]`);
            if (submissionElement) {
                submissionElement.remove();
            }
            alert("Submission deleted successfully!");
        } else if (response.status === 403) {
            alert("Unauthorized: Admin privileges are required to delete this submission.");
        } else {
            alert("Failed to delete the submission.");
        }
    })
    .catch(error => {
        console.error("Error during deletion:", error);
        alert("An error occurred while trying to delete the submission.");
    });
}

// Attach event listeners once the DOM is fully loaded.
document.addEventListener("DOMContentLoaded", function() {
    // Attach listeners for delete buttons for artist submissions.
    const deleteButtons = document.querySelectorAll(".delete-button");
    deleteButtons.forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault(); // Prevent the default form submission.
            const submissionId = event.target.closest(".rank-item").dataset.id;
            deleteSubmission(submissionId);
        });
    });

    // Attach listeners for youth delete buttons.
    const youthDeleteButtons = document.querySelectorAll(".youth-delete-container .delete-btn");
    youthDeleteButtons.forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault(); // Prevent any default action.
            const submissionId = event.target.closest(".rank-item").dataset.id;
            deleteYouthSubmission(submissionId);
        });
    });
});
