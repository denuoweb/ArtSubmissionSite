// static/js/form_validation.js

document.addEventListener("DOMContentLoaded", () => {
    // URL for deleting cached images, passed from the server
    const deleteCachedImageUrl = window.deleteCachedImageUrl || '/delete_cached_image';
    
    const maxBadgeUploads = 3;
    const addBadgeBtn = document.getElementById("addBadgeUpload");
    const badgeUploadContainer = document.getElementById("badgeUploadContainer");
    const form = document.getElementById("submissionForm");
    const emailField = document.getElementById("email");
    const emailErrorContainer = document.getElementById("email-error");
    const phoneField = document.getElementById("phone_number");
    const phoneErrorContainer = document.getElementById("phone_number-error");

    if (phoneField) {
        phoneField.addEventListener("blur", validatePhoneNumber);
    }

    let emailIsValid = false;
    let badgeUploadCounter = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;

    if (!emailField || !form) {
        console.error("Required elements (email field or form) are missing.");
        return;
    }

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
            emailIsValid = false;
            return false;
        }

        const isAvailable = await checkEmailAvailability(email);
        if (!isAvailable) {
            emailErrorContainer.textContent = "This email is already in use.";
            emailErrorContainer.style.display = "block";
            emailIsValid = false;
            return false;
        } else {
            emailErrorContainer.textContent = "";
            emailErrorContainer.style.display = "none";
            emailIsValid = true;
        }
        return true;
    }

    // Trigger email validation on blur
    emailField.addEventListener("blur", validateEmail);

    // Single submit event listener
    form.addEventListener("submit", async (event) => {
        let formIsValid = true;

        // Prevent form submission until all validations are complete
        event.preventDefault();

        // Clear any existing general errors
        const generalError = document.getElementById("general-error");
        if (generalError) {
            generalError.style.display = "none";
            generalError.textContent = "";
        }

        // Validate email
        const emailCheck = await validateEmail();
        if (!emailCheck) {
            formIsValid = false;
            emailField.focus();
            alert("Invalid email! Please fix the email before submitting.");
        }
        
        // Validate phone number
        const phoneCheck = validatePhoneNumber();
        if (!phoneCheck) {
            formIsValid = false;
            if (formIsValid) phoneField.focus();
            alert("Invalid phone number! Please fix the phone number before submitting.");
        }

        // Validate required fields
        const requiredFields = form.querySelectorAll("[required]");
        requiredFields.forEach(field => {
            const errorContainer = document.getElementById(`${field.id}-error`);
            if (!field.checkValidity()) {
                if (errorContainer) {
                    errorContainer.textContent = field.validationMessage || "This field is required.";
                    errorContainer.style.display = "block";
                }
                if (formIsValid) field.focus();
                formIsValid = false;
            } else if (errorContainer) {
                errorContainer.textContent = "";
                errorContainer.style.display = "none";
            }
        });

        if (formIsValid) {
            // All validations passed, submit the form
            form.submit();
        }
    });

    function updateAddBadgeButton() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        addBadgeBtn.disabled = currentUploads >= maxBadgeUploads;
        addBadgeBtn.style.display = currentUploads >= maxBadgeUploads ? "none" : "block";
    }

    function populateBadgeDropdown(selectElement, badgeData) {
        selectElement.innerHTML = '<option value="" disabled selected>Select a Badge</option>';
        badgeData.forEach(badge => {
            const option = document.createElement("option");
            option.value = badge.id;
            option.textContent = `${badge.name}: ${badge.description}`;
            selectElement.appendChild(option);
        });
    }

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

    function addBadgeUpload() {
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
        fetchAndPopulateBadgeDropdown(badgeSelect);

        renumberBadgeUploads();
        updateAddBadgeButton();
    }

    // Event delegation for "Remove" buttons
    badgeUploadContainer.addEventListener("click", async (event) => {
        if (event.target && event.target.matches(".removeBadgeUpload")) {
            const button = event.target;
            const badgeUploadUnit = button.closest(".badge-upload-unit");
            const cachedFilePath = button.getAttribute('data-file-path') || badgeUploadUnit.querySelector('input[type="file"]').getAttribute('data-existing') || badgeUploadUnit.querySelector('input[type="hidden"]').value;

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

    // Initialize badge uploads
    if (badgeUploadContainer.querySelectorAll(".badge-upload-unit").length === 0) {
        addBadgeUpload();
    } else {
        // Update the badgeUploadCounter to prevent index duplication
        badgeUploadCounter = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        renumberBadgeUploads();
    }

    addBadgeBtn.addEventListener("click", addBadgeUpload);

    updateAddBadgeButton();
});

// Function to validate phone number format
function validatePhoneNumberFormat(phone) {
    // Allowed characters: digits, spaces, hyphens, parentheses
    const phoneRegex = /^[\d\s\-\(\)]+$/;
    return phoneRegex.test(phone);
}

// Function to count digits in the phone number
function countDigits(phone) {
    const digits = phone.replace(/\D/g, '');
    return digits.length;
}

// Function to validate the phone number
function validatePhoneNumber() {
    const phoneField = document.getElementById("phone_number"); // Adjust ID if different
    const phoneErrorContainer = document.getElementById("phone_number-error");
    const phone = phoneField.value.trim();

    // Check format
    if (!validatePhoneNumberFormat(phone)) {
        phoneErrorContainer.textContent = "Phone number can only contain digits, spaces, hyphens, or parentheses.";
        phoneErrorContainer.style.display = "block";
        phoneField.classList.add("is-invalid");
        return false;
    }

    // Check digit count
    const digitCount = countDigits(phone);
    if (digitCount < 10 || digitCount > 15) {
        phoneErrorContainer.textContent = "Phone number must contain between 10 and 15 digits.";
        phoneErrorContainer.style.display = "block";
        phoneField.classList.add("is-invalid");
        return false;
    }

    // If valid
    phoneErrorContainer.textContent = "";
    phoneErrorContainer.style.display = "none";
    phoneField.classList.remove("is-invalid");
    phoneField.classList.add("is-valid");
    return true;
}