document.addEventListener("DOMContentLoaded", function () {
    const submissionDetailModal = document.getElementById("submissionDetailModal");
    const submissionDetailContent = document.getElementById("submission-detail-content");

    submissionDetailModal.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget; // Button that triggered the modal
        const submissionId = button.getAttribute("data-id");

        // Fetch submission details
        fetch(`/submission/details/${submissionId}`)
            .then(response => response.json())
            .then(data => {
                // Populate the modal with data
                submissionDetailContent.innerHTML = `
                    <h5>Name: ${data.name}</h5>
                    <p><strong>Email:</strong> ${data.email}</p>
                    <p><strong>Phone Number:</strong> ${data.phone_number || "N/A"}</p>
                    <p><strong>Artist Bio:</strong> ${data.artist_bio}</p>
                    <p><strong>Portfolio Link:</strong> ${data.portfolio_link ? `<a href="${data.portfolio_link}" target="_blank">${data.portfolio_link}</a>` : "N/A"}</p>
                    <p><strong>Statement:</strong> ${data.statement}</p>
                    <p><strong>Demographic Identity:</strong> ${data.demographic_identity || "N/A"}</p>
                    <p><strong>Lane County Connection:</strong> ${data.lane_county_connection || "N/A"}</p>
                    <p><strong>Accessibility Needs:</strong> ${data.accessibility_needs || "N/A"}</p>
                    <p><strong>Future Engagement:</strong> ${data.future_engagement || "N/A"}</p>
                    <p><strong>Consent to Data:</strong> ${data.consent_to_data ? "Yes" : "No"}</p>
                `;
            })
            .catch(error => {
                console.error("Error fetching submission details:", error);
                submissionDetailContent.innerHTML = `<p class="text-danger">An error occurred while loading submission details.</p>`;
            });
    });
});
