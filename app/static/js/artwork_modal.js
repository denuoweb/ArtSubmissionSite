function openArtworkModal(artworkUrl, name, submissionId, submissionType) {
    const modal = document.getElementById('artworkModal');
    const modalTitle = document.getElementById('artworkModalTitle');
    const badgeArtworkList = document.getElementById('modalBadgeArtworks');

    // Set the modal title
    modalTitle.textContent = name || 'Artwork Detail';

    // Clear the badge artwork list before loading new data
    badgeArtworkList.innerHTML = '';

    // --- Display the passed artwork image ---
    let modalImageContainer = document.getElementById('modalImageContainer');
    if (!modalImageContainer) {
        modalImageContainer = document.createElement('div');
        modalImageContainer.id = 'modalImageContainer';
        modalImageContainer.classList.add('mb-3');
        const modalBody = modal.querySelector('.modal-body');
        if (modalBody) {
            modalBody.insertBefore(modalImageContainer, modalBody.firstChild);
        }
    }
    // Clear any previous image
    modalImageContainer.innerHTML = '';
    const mainImage = document.createElement('img');
    mainImage.src = artworkUrl;
    mainImage.alt = "Artwork";
    mainImage.classList.add("img-fluid", "mb-3");
    modalImageContainer.appendChild(mainImage);
    // --- End display image ---

    if (!submissionId) {
        console.error('Invalid submission ID.');
        modalTitle.textContent = "Error: Submission ID not found.";
        return;
    }

    const basePath = document.querySelector('body').getAttribute('data-base-path') || "";

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

            // Reset common fields
            document.getElementById('modalSubmitterName').textContent = "";
            document.getElementById('modalEmail').textContent = "";
            document.getElementById('modalPhoneNumber').textContent = data.phone_number || "N/A";

            // Define arrays for fields unique to each submission type.
            const adultFields = ['modalArtistBio', 'modalPortfolioLink', 'modalStatement', 'modalDemographic', 'modalLaneCounty', 'modalHeard', 'modalFutureEngagement'];
            const youthFields = ['modalAge', 'modalParentContactInfo', 'modalAboutWhyDesign', 'modalAboutYourself', 'modalParentConsent'];

            // Hide all optional fields to start clean.
            adultFields.forEach(id => {
                const elem = document.getElementById(id);
                if (elem && elem.parentElement) {
                    elem.parentElement.style.display = 'none';
                }
            });
            youthFields.forEach(id => {
                const elem = document.getElementById(id);
                if (elem && elem.parentElement) {
                    elem.parentElement.style.display = 'none';
                }
            });

            // Populate common fields.
            document.getElementById('modalSubmitterName').textContent = data.name;
            document.getElementById('modalEmail').textContent = data.email;

            // Check the submission type and display the correct fields.
            if (submissionType === 'youth') {
                // Youth-specific fields.
                const ageElem = document.getElementById('modalAge');
                if (ageElem) {
                    ageElem.textContent = data.age;
                    ageElem.parentElement.style.display = '';
                }
                const parentContactElem = document.getElementById('modalParentContactInfo');
                if (parentContactElem) {
                    parentContactElem.textContent = data.parent_contact_info;
                    parentContactElem.parentElement.style.display = '';
                }
                const aboutWhyDesignElem = document.getElementById('modalAboutWhyDesign');
                if (aboutWhyDesignElem) {
                    aboutWhyDesignElem.textContent = data.about_why_design;
                    aboutWhyDesignElem.parentElement.style.display = '';
                }
                const aboutYourselfElem = document.getElementById('modalAboutYourself');
                if (aboutYourselfElem) {
                    aboutYourselfElem.textContent = data.about_yourself;
                    aboutYourselfElem.parentElement.style.display = '';
                }
                const parentConsentElem = document.getElementById('modalParentConsent');
                if (parentConsentElem) {
                    parentConsentElem.textContent = data.parent_consent ? "Yes" : "No";
                    parentConsentElem.parentElement.style.display = '';
                }
            } else {
                // Adult submission fields.
                const artistBioElem = document.getElementById('modalArtistBio');
                if (artistBioElem) {
                    artistBioElem.textContent = data.artist_bio;
                    artistBioElem.parentElement.style.display = '';
                }
                const artistPhoneElem = document.getElementById('modalPhoneNumber');
                if (artistPhoneElem) {
                    artistPhoneElem.textContent = data.phone_number;
                    artistPhoneElem.parentElement.style.display = '';
                }
                const portfolioLinkElem = document.getElementById('modalPortfolioLink');
                if (portfolioLinkElem) {
                    portfolioLinkElem.textContent = data.portfolio_link || 'N/A';
                    portfolioLinkElem.href = data.portfolio_link || '#';
                    portfolioLinkElem.parentElement.style.display = '';
                }
                const statementElem = document.getElementById('modalStatement');
                if (statementElem) {
                    statementElem.textContent = data.statement;
                    statementElem.parentElement.style.display = '';
                }
                const demographicElem = document.getElementById('modalDemographic');
                if (demographicElem) {
                    demographicElem.textContent = data.demographic_identity || 'N/A';
                    demographicElem.parentElement.style.display = '';
                }
                const laneCountyElem = document.getElementById('modalLaneCounty');
                if (laneCountyElem) {
                    laneCountyElem.textContent = data.lane_county_connection || 'N/A';
                    laneCountyElem.parentElement.style.display = '';
                }
                const heardElem = document.getElementById('modalHeard');
                if (heardElem) {
                    heardElem.textContent = data.hear_about_contest || 'N/A';
                    heardElem.parentElement.style.display = '';
                }
                const futureEngagementElem = document.getElementById('modalFutureEngagement');
                if (futureEngagementElem) {
                    futureEngagementElem.textContent = data.future_engagement || 'N/A';
                    futureEngagementElem.parentElement.style.display = '';
                }
            }
  
            // Populate the opt-in field (common to both types).
            const optInSpan = document.getElementById('modalFeaturedOptIn');
            optInSpan.textContent = data.opt_in_featured_artwork ? "Yes" : "No";

            // Optionally, populate badge artworks if available.
            if (data.badge_artworks && data.badge_artworks.length > 0) {
                data.badge_artworks.forEach(artwork => {
                    const li = document.createElement('li');
                    li.classList.add('list-group-item');
                    const badgeText = document.createElement('strong');
                    badgeText.textContent = "Badge ID: ";
                    li.appendChild(badgeText);
                    li.append(` ${artwork.badge_id} `);

                    const artworkLink = document.createElement('a');
                    artworkLink.href = artwork.artwork_file;
                    artworkLink.textContent = "View Artwork";
                    artworkLink.target = "_blank";
                    li.appendChild(artworkLink);

                    badgeArtworkList.appendChild(li);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching artwork details:', error);
            modalTitle.textContent = "Error loading submission details.";
        });

    // Show the modal.
    modal.style.display = 'block';
    modal.classList.add('show');
    document.body.classList.add('body-no-scroll');
    document.body.style.overflow = 'hidden';
}

function closeArtworkModal() {
    const modal = document.getElementById('artworkModal');
    modal.style.display = 'none';
    modal.classList.remove('show');
    document.body.classList.remove('body-no-scroll');
    document.body.style.overflow = '';
}

document.addEventListener("DOMContentLoaded", function () {
    const artworkThumbnails = document.querySelectorAll(".artwork-thumbnail");
    artworkThumbnails.forEach((thumbnail) => {
        thumbnail.addEventListener("click", function (event) {
            const imageUrl = event.target.dataset.artworkUrl;
            const name = event.target.dataset.name;
            const submissionId = event.target.dataset.id;
            const submissionType = event.target.dataset.type; // 'artist' or 'youth'
            openArtworkModal(imageUrl, name, submissionId, submissionType);
        });
    });
});
