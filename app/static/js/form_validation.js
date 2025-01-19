// static/js/form_validation.js

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------
    // Configuration and Element Selection
    // -------------------------
    const deleteCachedImageUrl = window.deleteCachedImageUrl || '/delete_cached_image';
    const maxBadgeUploads = 3;
    const addBadgeBtn = document.getElementById("addBadgeUpload");
    const badgeUploadContainer = document.getElementById("badgeUploadContainer");
    const form = document.getElementById("submissionForm");
    const emailField = document.getElementById("email");
    const emailErrorContainer = document.getElementById("email-error");
    const phoneField = document.getElementById("phone_number");
    const phoneErrorContainer = document.getElementById("phone_number-error");

    // -------------------------
    // Initial Checks
    // -------------------------
    if (!emailField || !form || !addBadgeBtn || !badgeUploadContainer) {
        console.error("Required elements (email field, form, add badge button, or badge upload container) are missing.");
        return;
    }

    // -------------------------
    // Email Validation Functions
    // -------------------------
    function validateEmailFormat(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    async function checkEmailAvailability(email) {
        try {
            const csrfToken = document.querySelector('input[name="csrf_token"]').value;
            const response = await fetch(`/api/check-email`, {  // Adjusted to relative path
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                console.error(`Server returned ${response.status}: ${response.statusText}`);
                throw new Error("Server error");
            }

            const result = await response.json();
            return result.isAvailable;
        } catch (error) {
            console.error("Error checking email availability:", error.message);
            alert("Unable to verify email at this time. Please try again later.");
            return false; // Assume email is unavailable if an error occurs
        }
    }

    async function validateEmail() {
        const email = emailField.value.trim();

        if (!validateEmailFormat(email)) {
            emailErrorContainer.textContent = "Invalid email format.";
            emailErrorContainer.style.display = "block";
            emailField.classList.add("is-invalid");
            emailField.classList.remove("is-valid");
            return false;
        }

        const isAvailable = await checkEmailAvailability(email);
        if (!isAvailable) {
            emailErrorContainer.textContent = "This email is already in use.";
            emailErrorContainer.style.display = "block";
            emailField.classList.add("is-invalid");
            emailField.classList.remove("is-valid");
            return false;
        } else {
            emailErrorContainer.textContent = "";
            emailErrorContainer.style.display = "none";
            emailField.classList.remove("is-invalid");
            emailField.classList.add("is-valid");
            return true;
        }
    }

    // Trigger email validation on blur
    emailField.addEventListener("blur", validateEmail);

    // -------------------------
    // Phone Number Validation Functions
    // -------------------------
    function validatePhoneNumberFormat(phone) {
        // Allowed characters: digits, spaces, hyphens, parentheses
        const phoneRegex = /^[\d\s\-\(\)]+$/;
        return phoneRegex.test(phone);
    }

    function countDigits(phone) {
        const digits = phone.replace(/\D/g, '');
        return digits.length;
    }

    function validatePhoneNumber() {
        if (!phoneField) return true; // If phone field is not present, skip validation

        const phone = phoneField.value.trim();

        // Check format
        if (!validatePhoneNumberFormat(phone)) {
            phoneErrorContainer.textContent = "Phone number can only contain digits, spaces, hyphens, or parentheses.";
            phoneErrorContainer.style.display = "block";
            phoneField.classList.add("is-invalid");
            phoneField.classList.remove("is-valid");
            return false;
        }

        // Check digit count
        const digitCount = countDigits(phone);
        if (digitCount < 10 || digitCount > 15) {
            phoneErrorContainer.textContent = "Phone number must contain between 10 and 15 digits.";
            phoneErrorContainer.style.display = "block";
            phoneField.classList.add("is-invalid");
            phoneField.classList.remove("is-valid");
            return false;
        }

        // If valid
        phoneErrorContainer.textContent = "";
        phoneErrorContainer.style.display = "none";
        phoneField.classList.remove("is-invalid");
        phoneField.classList.add("is-valid");
        return true;
    }

    // Attach phone number validation to blur event
    if (phoneField) {
        phoneField.addEventListener("blur", validatePhoneNumber);
    }

    // -------------------------
    // File Inputs Validation
    // -------------------------
    function validateFileInputs() {
        const fileInputs = form.querySelectorAll("input[type='file'][required]");
        let allValid = true;

        fileInputs.forEach(fileInput => {
            const errorContainer = document.getElementById(`${fileInput.id}-error`);
            // Only validate if there's no existing file path (i.e., no previously uploaded file)
            if (fileInput.files.length === 0 && !fileInput.getAttribute('data-existing')) {
                errorContainer.textContent = "Please upload your artwork file.";
                errorContainer.style.display = "block";
                fileInput.classList.add("is-invalid");
                fileInput.classList.remove("is-valid");
                allValid = false;
            } else {
                errorContainer.textContent = "";
                errorContainer.style.display = "none";
                fileInput.classList.remove("is-invalid");
                fileInput.classList.add("is-valid");
            }
        });

        return allValid;
    }

    // -------------------------
    // Badge Dropdown Management
    // -------------------------
    // Function to ensure "Select a Badge" is selected for all dropdowns if no selection exists
    function ensureSelectBadgeDefault() {
        const badgeSelects = badgeUploadContainer.querySelectorAll("select[name^='badge_uploads-'][name$='-badge_id']");
        badgeSelects.forEach(select => {
            if (!select.value) { // Only set if no value is selected
                const defaultOption = select.querySelector('option[value=""]');
                if (defaultOption) {
                    defaultOption.selected = true;
                }
            }
        });
    }

    // Function to populate badge dropdown and preserve existing selection
    async function fetchAndPopulateBadgeDropdown(selectElement) {
        try {
            const response = await fetch(`/api/badges`);  // Adjusted to relative path

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const badgeData = await response.json();  // Assuming the API returns JSON
            populateBadgeDropdown(selectElement, badgeData);
        } catch (error) {
            console.error("Error fetching badges:", error);
            alert("Unable to load badge options. Please try again later.");
        }
    }

    // Function to populate badge dropdown while preserving existing selection
    function populateBadgeDropdown(selectElement, badgeData) {
        const existingValue = selectElement.value; // Capture existing selected value

        // Clear existing options and add the default option
        selectElement.innerHTML = '<option value="" disabled selected>Select a Badge</option>';

        badgeData.forEach(badge => {
            const option = document.createElement("option");
            option.value = badge.id;
            option.textContent = `${badge.name}: ${badge.description}`;
            // Preserve selection if the badge ID matches the existing value
            if (badge.id === parseInt(existingValue)) { // Ensure type consistency
                option.selected = true;
            }
            selectElement.appendChild(option);
        });

        // If existing value is not in the fetched badges, reset to default
        const isExistingValueValid = badgeData.some(badge => badge.id === parseInt(existingValue));
        if (existingValue && !isExistingValueValid) {
            selectElement.value = "";
        }
    }

    // Function to renumber badge uploads
    function renumberBadgeUploads() {
        const badgeUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit");
        badgeUploads.forEach((upload, index) => {
            const legend = upload.querySelector("legend");
            if (legend) {
                legend.textContent = `Badge Upload ${index + 1}`;
            }

            // Update badge_id field
            const badgeSelect = upload.querySelector("select[name^='badge_uploads-'][name$='-badge_id']");
            if (badgeSelect) {
                badgeSelect.name = `badge_uploads-${index}-badge_id`;
                badgeSelect.id = `badge_uploads-${index}-badge_id`;
                // Update corresponding error container
                const badgeError = upload.querySelector(`#badge_uploads-${index}-badge_id-error`);
                if (badgeError) {
                    badgeError.id = `badge_uploads-${index}-badge_id-error`;
                }
            }

            // Update artwork_file field
            const artworkInput = upload.querySelector("input[type='file'][name^='badge_uploads-'][name$='-artwork_file']");
            if (artworkInput) {
                artworkInput.name = `badge_uploads-${index}-artwork_file`;
                artworkInput.id = `badge_uploads-${index}-artwork_file`;
                // Update corresponding error container
                const artworkError = upload.querySelector(`#badge_uploads-${index}-artwork_file-error`);
                if (artworkError) {
                    artworkError.id = `badge_uploads-${index}-artwork_file-error`;
                }
            }

            // Update cached_file_path hidden field
            const cachedInput = upload.querySelector("input[type='hidden'][name^='badge_uploads-'][name$='-cached_file_path']");
            if (cachedInput) {
                cachedInput.name = `badge_uploads-${index}-cached_file_path`;
            }

            // Update data-existing attribute on artwork file input
            if (artworkInput && cachedInput) {
                const existingFilePath = cachedInput.value;
                artworkInput.setAttribute('data-existing', existingFilePath);
            }

            // Update "Remove" button's data-file-path attribute
            const removeBtn = upload.querySelector(".removeBadgeUpload");
            if (removeBtn && cachedInput) {
                const filePath = cachedInput.value || "";
                removeBtn.setAttribute('data-file-path', filePath);
            }
        });
    }

    // Function to update the "Add Badge Upload" button's state
    function updateAddBadgeButton() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        addBadgeBtn.disabled = currentUploads >= maxBadgeUploads;
        addBadgeBtn.style.display = currentUploads >= maxBadgeUploads ? "none" : "block";
    }

    // Function to add a new badge upload section
    async function addBadgeUpload() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        if (currentUploads >= maxBadgeUploads) return;

        const uniqueIndex = badgeUploadCounter++;
        const newBadgeUpload = document.createElement("fieldset");
        newBadgeUpload.classList.add("badge-upload-unit", "border", "p-3", "mb-3");

        const badgeIdName = `badge_uploads-${uniqueIndex}-badge_id`;
        const artworkFileName = `badge_uploads-${uniqueIndex}-artwork_file`;
        const cachedFilePathName = `badge_uploads-${uniqueIndex}-cached_file_path`;  // Hidden field

        newBadgeUpload.innerHTML = `
            <legend>Badge Upload</legend>
            <div class="mb-3">
                <label for="${badgeIdName}">Select a Badge</label>
                <select class="form-select" id="${badgeIdName}" name="badge_uploads-${uniqueIndex}-badge_id" required>
                    <option value="" disabled selected>Select a Badge</option>
                </select>
                <div class="invalid-feedback" id="${badgeIdName}-error">Please select a badge.</div>
            </div>
            <div class="mb-3">
                <label for="${artworkFileName}">Upload Artwork</label>
                <input type="file" class="form-control" id="${artworkFileName}" name="badge_uploads-${uniqueIndex}-artwork_file" accept=".jpg,.jpeg,.png,.svg" data-existing="">
                <div class="invalid-feedback" id="${artworkFileName}-error">Please upload your artwork file.</div>
                <input type="hidden" name="${cachedFilePathName}" value="">
            </div>
            <button type="button" class="btn btn-danger btn-sm removeBadgeUpload" data-file-path="">Remove</button>
        `;
        badgeUploadContainer.appendChild(newBadgeUpload);

        const badgeSelect = document.getElementById(badgeIdName);
        await fetchAndPopulateBadgeDropdown(badgeSelect);

        // After populating, ensure default is selected
        const defaultOption = badgeSelect.querySelector('option[value=""]');
        if (defaultOption) {
            defaultOption.selected = true;
        }

        renumberBadgeUploads();
        updateAddBadgeButton();
    }

    // -------------------------
    // Event Delegation for "Remove" Buttons
    // -------------------------
    badgeUploadContainer.addEventListener("click", async (event) => {
        if (event.target && event.target.matches(".removeBadgeUpload")) {
            const button = event.target;
            const badgeUploadUnit = button.closest(".badge-upload-unit");
            const cachedFilePath = button.getAttribute('data-file-path') || 
                                    badgeUploadUnit.querySelector('input[type="file"]').getAttribute('data-existing') || 
                                    badgeUploadUnit.querySelector('input[type="hidden"]').value;

            if (cachedFilePath) {
                const csrfToken = document.querySelector('input[name="csrf_token"]').value;
                try {
                    const response = await fetch(deleteCachedImageUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ file_path: cachedFilePath })
                    });

                    if (!response.ok) {
                        throw new Error(`Server returned ${response.status}`);
                    }

                    const result = await response.json();
                    if (result.success) {
                        // Successfully deleted the file, remove the fieldset
                        badgeUploadContainer.removeChild(badgeUploadUnit);
                        renumberBadgeUploads();
                        updateAddBadgeButton();
                        alert("Badge upload removed successfully.");
                    } else {
                        throw new Error(result.message || "Failed to delete the file.");
                    }
                } catch (error) {
                    console.error("Error deleting cached image:", error);
                    alert("An error occurred while removing the badge upload. Please try again.");
                }
            } else {
                // No cached file, simply remove the fieldset
                badgeUploadContainer.removeChild(badgeUploadUnit);
                renumberBadgeUploads();
                updateAddBadgeButton();
            }
        }
    });

    // -------------------------
    // Initialization on Page Load
    // -------------------------
    async function initializeBadgeUploads() {
        const existingUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;

        if (existingUploads === 0) {
            await addBadgeUpload();
        } else {
            badgeUploadCounter = existingUploads;
            renumberBadgeUploads();

            // Populate existing badge upload dropdowns
            const existingBadgeSelects = badgeUploadContainer.querySelectorAll("select[name^='badge_uploads-'][name$='-badge_id']");
            for (const select of existingBadgeSelects) {
                await fetchAndPopulateBadgeDropdown(select);
            }
        }

        // Ensure default selection after initial population
        ensureSelectBadgeDefault();

        // Update the Add button's state
        updateAddBadgeButton();
    }

    initializeBadgeUploads();

    // Attach event listener for adding new badge uploads
    addBadgeBtn.addEventListener("click", addBadgeUpload);
});
