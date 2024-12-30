document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('badgeUploadContainer');
    const addBtn = document.getElementById('addBadgeUpload');

    let badgeData = [];

    // Fetch badge data from the server
    fetch('/api/badges')
        .then(response => response.json())
        .then(data => {
            badgeData = data; // Store the fetched badge data

            // Populate the initial dropdown
            const initialSelect = container.querySelector('select');
            if (initialSelect) {
                populateBadgeDropdown(initialSelect, badgeData);
                initializeChoices(initialSelect); // Initialize Choices.js
            }
        })
        .catch(error => console.error('Error fetching badge data:', error));

    // Function to populate a dropdown with badge data
    function populateBadgeDropdown(selectElement, badgeData) {
        selectElement.innerHTML = ""; // Clear existing options (if any)

        // Add a default "Select a Badge" option
        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "Select a Badge";
        defaultOption.disabled = true;
        defaultOption.selected = true;
        selectElement.appendChild(defaultOption);

        // Add options from badgeData
        badgeData.forEach(badge => {
            const option = document.createElement('option');
            option.value = badge.id;
            option.textContent = `${badge.name}: ${badge.description}`;
            selectElement.appendChild(option);
        });
    }

    // Initialize Choices.js on the dropdown
    function initializeChoices(selectElement) {
        new Choices(selectElement, {
            searchEnabled: true, // Enable searching
            itemSelectText: '', // No "press Enter to select" text
            placeholder: true,
            shouldSort: false, // Preserve server order
        });
    }

    // Add new badge and artwork upload fields dynamically
    addBtn.addEventListener('click', function () {
        const newBadgeUnit = document.createElement('fieldset');
        newBadgeUnit.classList.add('badge-upload-unit');

        // Add legend to group the set
        const legend = document.createElement('legend');
        legend.textContent = "Badge Upload";
        newBadgeUnit.appendChild(legend);

        // Badge selection dropdown
        const badgeSelectWrapper = document.createElement('p');
        const badgeLabel = document.createElement('label');
        badgeLabel.setAttribute('for', 'badge_id');
        badgeLabel.textContent = "Select a Badge";
        const badgeSelect = document.createElement('select');
        badgeSelect.name = 'badge_id[]';
        badgeSelect.classList.add('form-select');
        badgeSelect.required = true;
        populateBadgeDropdown(badgeSelect, badgeData); // Populate options
        badgeSelectWrapper.appendChild(badgeLabel);
        badgeSelectWrapper.appendChild(badgeSelect);
        newBadgeUnit.appendChild(badgeSelectWrapper);

        // Initialize Choices.js on the new dropdown
        initializeChoices(badgeSelect);

        // Artwork upload input
        const artworkUploadWrapper = document.createElement('p');
        const artworkLabel = document.createElement('label');
        artworkLabel.setAttribute('for', 'artwork_file');
        artworkLabel.textContent = "Upload Artwork";
        const artworkUpload = document.createElement('input');
        artworkUpload.type = 'file';
        artworkUpload.name = 'artwork_file[]';
        artworkUpload.accept = '.jpg,.jpeg,.png,.svg,.png';
        artworkUpload.required = true;
        artworkUploadWrapper.appendChild(artworkLabel);
        artworkUploadWrapper.appendChild(artworkUpload);
        newBadgeUnit.appendChild(artworkUploadWrapper);

        // Remove button
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.classList.add('remove-badge-upload', 'btn', 'btn-danger', 'btn-sm');
        removeButton.textContent = 'Remove';

        // Remove button event listener
        removeButton.addEventListener('click', function (event) {
            event.stopPropagation();
            container.removeChild(newBadgeUnit);
        });

        newBadgeUnit.appendChild(removeButton);

        // Append the new badge unit to the container
        container.appendChild(newBadgeUnit);
    });
});
