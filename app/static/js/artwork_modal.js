function openArtworkModal(imageUrl, title) {
    const modal = document.getElementById('artworkModal');
    const modalImage = document.getElementById('artworkModalImage');
    const modalTitle = document.getElementById('artworkModalTitle');

    // Set the image URL and title for the modal
    modalImage.src = imageUrl;
    modalTitle.textContent = title || 'Artwork Detail';

    // Show the modal
    modal.style.display = 'block';
    modal.classList.add('show');
    document.body.classList.add('body-no-scroll'); // Prevent scrolling when modal is open
}

function closeArtworkModal() {
    const modal = document.getElementById('artworkModal');

    // Hide the modal
    modal.style.display = 'none';
    modal.classList.remove('show');
    document.body.classList.remove('body-no-scroll'); // Restore scrolling
}

document.addEventListener("DOMContentLoaded", function() {
    // Select all elements that should open the artwork modal
    const artworkThumbnails = document.querySelectorAll(".artwork-thumbnail");
  
    artworkThumbnails.forEach((thumbnail) => {
      thumbnail.addEventListener("click", function(event) {
        // Extract data from custom attributes
        const imageUrl = event.target.dataset.artworkUrl;
        const name = event.target.dataset.name;
  
        // Call the modal logic you already have
        openArtworkModal(imageUrl, name);
      });
    });
  });
  