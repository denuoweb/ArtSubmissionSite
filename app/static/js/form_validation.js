document.addEventListener("DOMContentLoaded", () => {
    const maxBadgeUploads = 3;
    const addBadgeBtn = document.getElementById("addBadgeUpload");
    const badgeUploadContainer = document.getElementById("badgeUploadContainer");
    const form = document.getElementById("submissionForm");

    const fileInputs = document.querySelectorAll("input[type='file'][data-existing]");
    fileInputs.forEach(input => {
        const existingFile = input.dataset.existing;
        if (existingFile) {
            const fileLabel = document.createElement("p");
            fileLabel.className = "existing-file";
            fileLabel.textContent = `Previously uploaded: ${existingFile}`;
            input.parentNode.insertBefore(fileLabel, input);
        }
    });

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

    initializeExistingChoices();
    updateAddBadgeButton();

    let badgeIndexCounter = badgeUploadContainer.querySelectorAll('.badge-upload-unit').length;
    let availableIndices = [];

    function updateAddBadgeButton() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        addBadgeBtn.disabled = currentUploads >= maxBadgeUploads;

        if (currentUploads >= maxBadgeUploads) {
            addBadgeBtn.style.display = "disable"
        } else {
            addBadgeBtn.style.display = "block";
        }
    }

    function populateBadgeDropdown(selectElement, badgeData) {
        selectElement.innerHTML = "";
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Select a Badge";
        defaultOption.disabled = true;
        defaultOption.selected = true;
        selectElement.appendChild(defaultOption);

        badgeData.forEach((badge) => {
            const option = document.createElement("option");
            option.value = badge.id;
            option.textContent = `${badge.name}: ${badge.description}`;
            selectElement.appendChild(option);
        });
    }

    function attachValidationListeners(field, choicesInstance = null) {
        if (field.tagName.toLowerCase() === "select" || field.type === "file") {
            field.addEventListener("change", () => {
                if (field.tagName.toLowerCase() === "select") {
                    updateBadgeOptions();
                }
            });
        }

        if (choicesInstance) {
            choicesInstance.passedElement.element.addEventListener("change", () => {
                updateBadgeOptions();
            });
        }
    }

    addBadgeBtn.addEventListener("click", () => {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        if (currentUploads >= maxBadgeUploads) {
            alert(`You can only upload artwork for up to ${maxBadgeUploads} badges.`);
            return;
        }

        let newIndex;
        if (availableIndices.length > 0) {
            newIndex = availableIndices.pop();
        } else {
            newIndex = badgeIndexCounter;
            badgeIndexCounter++;
        }

        const newBadgeUpload = document.createElement("fieldset");
        newBadgeUpload.classList.add("badge-upload-unit", "border", "p-3", "mb-3");

        const badgeIdName = `badge_uploads-${newIndex}-badge_id`;
        const artworkFileName = `badge_uploads-${newIndex}-artwork_file`;
        const badgeIdId = badgeIdName;
        const artworkFileId = artworkFileName;

        const badgeSelectHTML = `
            <div class="mb-3">
                <label for="${badgeIdId}">Select a Badge</label>
                <select class="form-select" id="${badgeIdId}" name="${badgeIdName}">
                    <option value="" disabled selected>Select a Badge</option>
                </select>
            </div>
        `;

        const artworkUploadHTML = `
            <div class="mb-3">
                <label for="${artworkFileId}">Upload Artwork</label>
                <input type="file" class="form-control" id="${artworkFileId}" name="${artworkFileName}" accept=".jpg,.jpeg,.png,.svg">
            </div>
        `;

        const removeButtonHTML = `
            <button type="button" class="btn btn-danger btn-sm removeBadgeUpload">Remove</button>
        `;

        newBadgeUpload.innerHTML = `<legend>Badge Upload ${newIndex + 1}</legend>${badgeSelectHTML}${artworkUploadHTML}${removeButtonHTML}`;
        badgeUploadContainer.appendChild(newBadgeUpload);

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
                updateBadgeOptions();
            })
            .catch((error) => console.error("Error fetching badge data:", error));

        const artworkInput = document.getElementById(artworkFileId);

        const removeButton = newBadgeUpload.querySelector(".removeBadgeUpload");
        removeButton.addEventListener("click", () => {
            badgeUploadContainer.removeChild(newBadgeUpload);
            availableIndices.push(newIndex);
            updateAddBadgeButton();
            updateBadgeOptions();
        });

        updateAddBadgeButton();
    });

    function updateBadgeOptions() {
        const allSelects = badgeUploadContainer.querySelectorAll("select[name^='badge_uploads-'][name$='-badge_id']");
        const selectedValues = Array.from(allSelects)
            .map(select => select.value)
            .filter(value => value !== "");

        allSelects.forEach(select => {
            const choicesInstance = select._choices;
            if (choicesInstance) {
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
            } else if (field.validity.rangeUnderflow || field.validity.rangeOverflow) {
                showError(field, errorContainer, "Please provide a valid age.");
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

        const fileInputs = document.querySelectorAll("input[type='file'][data-existing]");
        fileInputs.forEach(input => {
            if (input.files.length === 0 && input.dataset.existing) {
                const hiddenInput = document.createElement("input");
                hiddenInput.type = "hidden";
                hiddenInput.name = input.name;
                hiddenInput.value = input.dataset.existing;
                form.appendChild(hiddenInput);
                input.removeAttribute("name");
            }
        });
        
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