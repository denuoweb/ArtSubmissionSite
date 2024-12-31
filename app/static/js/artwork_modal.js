function openArtworkModal(_, name, submissionId) {
  const modal = document.getElementById('artworkModal');
  const modalTitle = document.getElementById('artworkModalTitle');
  const badgeArtworkList = document.getElementById('modalBadgeArtworks');

  // Set the modal title
  modalTitle.textContent = name || 'Artwork Detail';

  // Clear the badge artwork list before loading new data
  badgeArtworkList.innerHTML = '';

  if (!submissionId) {
      console.error('Invalid submission ID.');
      modalTitle.textContent = "Error: Submission ID not found.";
      return;
  }

  // Fetch artwork details from the API
  fetch(`/api/artwork-detail/${submissionId}`)
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

          // Populate artwork details dynamically
          if (data.badge_artworks && data.badge_artworks.length > 0) {
              data.badge_artworks.forEach(artwork => {
                  const badgeItem = document.createElement('li');
                  badgeItem.className = 'list-group-item';
                  badgeItem.innerHTML = `<strong>Badge ${artwork.badge_id}:</strong> <img src="${artwork.artwork_file}" alt="Badge Artwork" class="img-fluid mb-3">`;
                  badgeArtworkList.appendChild(badgeItem);
              });
          } else {
              const noArtworkItem = document.createElement('li');
              noArtworkItem.className = 'list-group-item';
              noArtworkItem.textContent = 'No badge artworks available.';
              badgeArtworkList.appendChild(noArtworkItem);
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
          document.getElementById('modalAccessibility').textContent = data.accessibility_needs || 'N/A';
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

  // Prevent background from scrolling
  document.body.style.overflow = 'hidden';
}

function closeArtworkModal() {
  const modal = document.getElementById('artworkModal');

  // Hide the modal
  modal.style.display = 'none';
  modal.classList.remove('show');
  document.body.classList.remove('body-no-scroll'); // Restore scrolling

  // Restore background scrolling
  document.body.style.overflow = '';
}


document.addEventListener("DOMContentLoaded", function () {
  // Select all elements that should open the artwork modal
  const artworkThumbnails = document.querySelectorAll(".artwork-thumbnail");

  artworkThumbnails.forEach((thumbnail) => {
      thumbnail.addEventListener("click", function (event) {
          // Extract data from custom attributes
          const imageUrl = event.target.dataset.artworkUrl;
          const name = event.target.dataset.name;
          const submissionId = event.target.dataset.id;

          // Call the modal logic
          openArtworkModal(imageUrl, name, submissionId);
      });
  });
});
