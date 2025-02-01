function openArtworkModal(artworkUrl, name, submissionId, submissionType) {
    const modal = document.getElementById('artworkModal');
    const modalTitle = document.getElementById('artworkModalTitle');
    const badgeArtworkList = document.getElementById('modalBadgeArtworks');
  
    // Set the modal title
    modalTitle.textContent = name || 'Artwork Detail';
  
    // Clear the badge artwork list before loading new data
    badgeArtworkList.innerHTML = '';
  
    // --- NEW CODE: Display the passed artwork image ---
    let modalImageContainer = document.getElementById('modalImageContainer');
    if (!modalImageContainer) {
        modalImageContainer = document.createElement('div');
        modalImageContainer.id = 'modalImageContainer';
        modalImageContainer.classList.add('mb-3');
        // Insert the image container at the top of the modal body
        const modalBody = modal.querySelector('.modal-body');
        if (modalBody) {
            modalBody.insertBefore(modalImageContainer, modalBody.firstChild);
        }
    }
    // Clear previous image (if any)
    modalImageContainer.innerHTML = '';
    // Create an image element using the passed artworkUrl
    const mainImage = document.createElement('img');
    mainImage.src = artworkUrl;
    mainImage.alt = "Artwork";
    mainImage.classList.add("img-fluid", "mb-3");
    modalImageContainer.appendChild(mainImage);
    // --- END NEW CODE ---
  
    if (!submissionId) {
        console.error('Invalid submission ID.');
        modalTitle.textContent = "Error: Submission ID not found.";
        return;
    }
  
    const basePath = document.querySelector('body').getAttribute('data-base-path') || "";
  
    // Continue to fetch additional artwork details from the API
    fetch(`${basePath}/api/artwork-detail/${submissionType}/${submissionId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Artwork details could not be loaded.');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error(data.error);
                modalTitle.textContent = "Error: Submission not found.";
                return;
            }
  
            // Populate other modal fields
            document.getElementById('modalSubmitterName').textContent = data.name;
            document.getElementById('modalEmail').textContent = data.email;
            document.getElementById('modalArtistBio').textContent = data.artist_bio;
            const portfolioLink = document.getElementById('modalPortfolioLink');
            portfolioLink.textContent = data.portfolio_link || 'N/A';
            portfolioLink.href = data.portfolio_link || '#';
            document.getElementById('modalStatement').textContent = data.statement;
            document.getElementById('modalDemographic').textContent = data.demographic_identity || 'N/A';
            document.getElementById('modalLaneCounty').textContent = data.lane_county_connection || 'N/A';
            document.getElementById('modalAccessibility').textContent = data.hear_about_contest || 'N/A';
            document.getElementById('modalFutureEngagement').textContent = data.future_engagement || 'N/A';
            const optInSpan = document.getElementById('modalFeaturedOptIn');
            optInSpan.textContent = data.opt_in_featured_artwork ? "Yes" : "No";
        })
        .catch(error => {
            console.error('Error fetching artwork details:', error);
            modalTitle.textContent = "Error loading submission details.";
        });
  
    // Show the modal
    modal.style.display = 'block';
    modal.classList.add('show');
    document.body.classList.add('body-no-scroll'); // Prevent scrolling when modal is open
    document.body.style.overflow = 'hidden';
}
  
function closeArtworkModal() {
    const modal = document.getElementById('artworkModal');
    // Hide the modal
    modal.style.display = 'none';
    modal.classList.remove('show');
    document.body.classList.remove('body-no-scroll');
    document.body.style.overflow = '';
}
  
document.addEventListener("DOMContentLoaded", function () {
    // Attach event listeners to all artwork-thumbnail links
    const artworkThumbnails = document.querySelectorAll(".artwork-thumbnail");
  
    artworkThumbnails.forEach((thumbnail) => {
        thumbnail.addEventListener("click", function (event) {
            // Extract data from custom attributes
            const imageUrl = event.target.dataset.artworkUrl;
            const name = event.target.dataset.name;
            const submissionId = event.target.dataset.id;
            const submissionType = event.target.dataset.type; // new parameter
  
            // Call the modal logic with the dynamic imageUrl passed along
            openArtworkModal(imageUrl, name, submissionId, submissionType);
        });
    });
});
