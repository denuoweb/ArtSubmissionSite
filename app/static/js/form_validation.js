// form_handler.js

document.addEventListener("DOMContentLoaded", () => {
    const maxBadgeUploads = 3;  // Maximum number of badge uploads allowed
    const addBadgeBtn = document.getElementById("addBadgeUpload");
    const badgeUploadContainer = document.getElementById("badgeUploadContainer");
    const form = document.getElementById("submissionForm");

    // Initialize Choices.js for existing badge_uploads
    const initializeExistingChoices = () => {
        const badgeSelects = badgeUploadContainer.querySelectorAll("select[name^='badge_uploads-'][name$='-badge_id']");
        badgeSelects.forEach(select => {
            const choicesInstance = new Choices(select, {
                searchEnabled: true,
                itemSelectText: "Select",
                placeholder: true,
                placeholderValue: "Select a Badge",
                shouldSort: true,
                removeItemButton: true,
            });
            attachValidationListeners(select, choicesInstance);
        });
    };

    // Call on page load
    initializeExistingChoices();
    updateAddBadgeButton();

    // Function to check and update the state of the Add Badge button
    function updateAddBadgeButton() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
    
        // Disable the button if max uploads reached
        addBadgeBtn.disabled = currentUploads >= maxBadgeUploads;
    
        // Hide the button if max uploads reached, otherwise show it
        if (currentUploads >= maxBadgeUploads) {
            addBadgeBtn.style.display = "none"; // Hide the button
        } else {
            addBadgeBtn.style.display = "block"; // Show the button
        }
    }

    // Function to populate a dropdown with badge data
    function populateBadgeDropdown(selectElement, badgeData) {
        selectElement.innerHTML = ""; // Clear existing options

        // Add a default "Select a Badge" option
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Select a Badge";
        defaultOption.disabled = true;
        defaultOption.selected = true;
        selectElement.appendChild(defaultOption);

        // Add options from badgeData
        badgeData.forEach((badge) => {
            const option = document.createElement("option");
            option.value = badge.id;
            option.textContent = `${badge.name}: ${badge.description}`;
            selectElement.appendChild(option);
        });
    }

    // Function to attach validation listeners to a field
    function attachValidationListeners(field, choicesInstance = null) {
        if (field.tagName.toLowerCase() === "select" || field.type === "file") {
            field.addEventListener("change", () => {
                validateField(field);
                if (field.tagName.toLowerCase() === "select") {
                    updateBadgeOptions();
                }
            });
        } else {
            field.addEventListener("input", () => {
                validateField(field);
            });
        }

        // If using Choices.js, listen for Choices-specific events
        if (choicesInstance) {
            choicesInstance.passedElement.element.addEventListener("change", () => {
                validateField(field);
                updateBadgeOptions();
            });
        }
    }

    // Event listener for adding a new badge upload unit
    addBadgeBtn.addEventListener("click", () => {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        if (currentUploads >= maxBadgeUploads) {
            alert(`You can only upload artwork for up to ${maxBadgeUploads} badges.`);
            return;
        }

        const newIndex = currentUploads;  // Zero-based index

        // Create a new badge upload unit
        const newBadgeUpload = document.createElement("fieldset");
        newBadgeUpload.classList.add("badge-upload-unit", "border", "p-3", "mb-3");

        // Generate unique IDs based on the new index
        const badgeIdName = `badge_uploads-${newIndex}-badge_id`;
        const artworkFileName = `badge_uploads-${newIndex}-artwork_file`;
        const badgeIdId = `${badgeIdName}`;
        const artworkFileId = `${artworkFileName}`;

        // Badge selection HTML
        const badgeSelectHTML = `
            <div class="mb-3">
                <label for="${badgeIdId}">Select a Badge</label>
                <select class="form-select" id="${badgeIdId}" name="${badgeIdName}" required>
                    <option value="" disabled selected>Select a Badge</option>
                </select>
                <div class="invalid-feedback" id="${badgeIdId}-error">Please select a badge.</div>
            </div>
        `;

        // Artwork file upload HTML
        const artworkUploadHTML = `
            <div class="mb-3">
                <label for="${artworkFileId}">Upload Artwork</label>
                <input type="file" class="form-control" id="${artworkFileId}" name="${artworkFileName}" accept=".jpg,.jpeg,.png,.svg" required>
                <div class="invalid-feedback" id="${artworkFileId}-error">Please upload your artwork file.</div>
            </div>
        `;

        // Remove button HTML
        const removeButtonHTML = `
            <button type="button" class="btn btn-danger btn-sm removeBadgeUpload">Remove</button>
        `;

        // Assemble the badge upload unit
        newBadgeUpload.innerHTML = `<legend>Badge Upload ${newIndex + 1}</legend>${badgeSelectHTML}${artworkUploadHTML}${removeButtonHTML}`;

        // Append the new badge upload unit to the container
        badgeUploadContainer.appendChild(newBadgeUpload);

        // Populate the badge dropdown with data
        const badgeSelect = document.getElementById(badgeIdId);
        fetch("/api/badges")
            .then((response) => response.json())
            .then((badgeData) => {
                populateBadgeDropdown(badgeSelect, badgeData);
                const choicesInstance = new Choices(badgeSelect, {
                    searchEnabled: true,
                    itemSelectText: "",
                    placeholder: true,
                    shouldSort: false,
                    removeItemButton: true,
                });
                attachValidationListeners(badgeSelect, choicesInstance);
                updateBadgeOptions(); // Update badge options after adding a new select
            })
            .catch((error) => console.error("Error fetching badge data:", error));

        // Attach validation listeners to the new file input
        const artworkInput = document.getElementById(artworkFileId);
        if (artworkInput) {
            attachValidationListeners(artworkInput);
        }

        // Add remove button functionality
        const removeButton = newBadgeUpload.querySelector(".removeBadgeUpload");
        removeButton.addEventListener("click", () => {
            badgeUploadContainer.removeChild(newBadgeUpload);
            updateAddBadgeButton(); // Update the Add Badge button state
            updateBadgeOptions(); // Update badge options to re-enable any disabled badges
        });

        updateAddBadgeButton(); // Update the Add Badge button state
    });

    // Function to update badge options across all dropdowns to prevent duplicate selections
    function updateBadgeOptions() {
        const allSelects = badgeUploadContainer.querySelectorAll("select[name^='badge_uploads-'][name$='-badge_id']");
        const selectedValues = Array.from(allSelects)
            .map(select => select.value)
            .filter(value => value !== "");

        allSelects.forEach(select => {
            const choicesInstance = select._choices;
            if (choicesInstance) {
                // Iterate through all options in Choices.js
                choicesInstance.store.options.forEach(option => {
                    const choiceValue = option.value;
                    const isSelectedElsewhere = selectedValues.includes(choiceValue) && choiceValue !== select.value;
                    if (isSelectedElsewhere) {
                        choicesInstance.disable(choiceValue, true);
                    } else {
                        choicesInstance.disable(choiceValue, false);
                    }
                });
            }
        });
    }

    // --- Validation Logic ---

    // Function to validate a single field
    function validateField(field) {
        const fieldId = field.id;
        const errorContainer = document.getElementById(`${fieldId}-error`);

        if (!errorContainer) {
            console.warn(`Error container for "${fieldId}" not found.`);
            return;
        }

        // Special handling for file inputs
        if (field.type === "file") {
            if (field.files.length === 0 || !field.files[0]) {
                showError(field, errorContainer, "Please upload your artwork file.");
            } else {
                // Validate file type
                const file = field.files[0];
                const allowedExtensions = [".jpg", ".jpeg", ".png", ".svg"];
                const fileExt = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

                if (!allowedExtensions.includes(fileExt)) {
                    showError(field, errorContainer, "Only JPG, JPEG, PNG, or SVG files are allowed.");
                    return;
                }

                // Optionally, validate file size here
                // Example: Max 8MB
                const maxSizeMB = 8;
                if (file.size > maxSizeMB * 1024 * 1024) {
                    showError(field, errorContainer, `File size must be less than ${maxSizeMB} MB.`);
                    return;
                }
                field.classList.add("is-valid");
                // If all validations pass
                clearError(field, errorContainer);
            }
            return;
        }

        // Check if the field is valid
        if (!field.checkValidity()) {
            if (field.validity.valueMissing) {
                showError(field, errorContainer, "This field is required.");
            } else if (field.validity.typeMismatch) {
                showError(field, errorContainer, "Please enter a valid value.");
            } else if (field.validity.tooShort) {
                showError(field, errorContainer, `Please lengthen this text to at least ${field.minLength} characters.`);
            } else if (field.validity.tooLong) {
                showError(field, errorContainer, `Please shorten this text to no more than ${field.maxLength} characters.`);
            } else {
                showError(field, errorContainer, "Invalid input.");
            }
        } else {
            clearError(field, errorContainer);
        }
    }

    // Show error message
    function showError(field, errorContainer, message) {
        field.classList.add("is-invalid");
        errorContainer.textContent = message;
        errorContainer.style.display = "block";
    }

    // Clear error message
    function clearError(field, errorContainer) {
        field.classList.remove("is-invalid");
        errorContainer.textContent = "";
        errorContainer.style.display = "none";
    }

    // Form submission handling
    form.addEventListener("submit", (event) => {
        // Prevent default submission to handle validation
        event.preventDefault();

        let formIsValid = true;

        // Validate all required fields
        const requiredFields = form.querySelectorAll("[required]");
        requiredFields.forEach((field) => {
            validateField(field);
            if (!field.checkValidity()) {
                formIsValid = false;
            }
        });

        // Additional validation for unique badge selections
        if (!validateUniqueBadges()) {
            formIsValid = false;
        }

        if (formIsValid) {
            // Optionally, you can disable the submit button to prevent multiple submissions
            const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
            }

            // Submit the form
            form.submit();
        } else {
            // Optionally, focus the first invalid field
            const firstInvalid = form.querySelector(".is-invalid");
            if (firstInvalid) {
                firstInvalid.focus();
            }
        }
    });

    // Function to validate unique badge selections
    function validateUniqueBadges() {
        const allSelects = badgeUploadContainer.querySelectorAll("select[name^='badge_uploads-'][name$='-badge_id']");
        const selectedValues = Array.from(allSelects)
            .map(select => select.value)
            .filter(value => value !== "");

        const duplicates = selectedValues.filter((item, index) => selectedValues.indexOf(item) !== index);

        if (duplicates.length > 0) {
            // Find all select elements with duplicate values and show errors
            allSelects.forEach(select => {
                if (duplicates.includes(select.value)) {
                    const errorContainer = document.getElementById(`${select.id}-error`);
                    if (errorContainer) {
                        showError(select, errorContainer, "This badge has already been selected.");
                    }
                }
            });
            return false;
        }

        // Clear duplicate errors if any
        allSelects.forEach(select => {
            const errorContainer = document.getElementById(`${select.id}-error`);
            if (errorContainer && errorContainer.textContent === "This badge has already been selected.") {
                clearError(select, errorContainer);
            }
        });

        return true;
    }
});
