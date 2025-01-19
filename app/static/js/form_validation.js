document.addEventListener("DOMContentLoaded", () => {
    const maxBadgeUploads = 3;
    const addBadgeBtn = document.getElementById("addBadgeUpload");
    const badgeUploadContainer = document.getElementById("badgeUploadContainer");
    const form = document.getElementById("submissionForm");
    const emailField = document.getElementById("email");
    const emailErrorContainer = document.getElementById("email-error");

    let emailIsValid = false;

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
        } else {
            // If the form is invalid, display a general error message
            if (!generalError) {
                displayFormError("Please correct the highlighted errors before submitting the form.");
            }
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

    function addBadgeUpload() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        if (currentUploads >= maxBadgeUploads) return;

        const index = currentUploads;
        const newBadgeUpload = document.createElement("fieldset");
        newBadgeUpload.classList.add("badge-upload-unit", "border", "p-3", "mb-3");

        const badgeIdName = `badge_uploads-${index}-badge_id`;
        const artworkFileName = `badge_uploads-${index}-artwork_file`;
        const cachedFilePathName = `badge_uploads-${index}-cached_file_path`;  // Hidden field

        newBadgeUpload.innerHTML = `
            <legend>Badge Upload ${index + 1}</legend>
            <div class="mb-3">
                <label for="${badgeIdName}">Select a Badge</label>
                <select class="form-select" id="${badgeIdName}" name="${badgeIdName}" required>
                    <option value="" disabled selected>Select a Badge</option>
                </select>
                <p class="text-danger small" id="${badgeIdName}-error"></p>
            </div>
            <div class="mb-3">
                <label for="${artworkFileName}">Upload Artwork</label>
                <input type="file" class="form-control" id="${artworkFileName}" name="${artworkFileName}" accept=".jpg,.jpeg,.png,.svg" required>
                <p class="text-danger small" id="${artworkFileName}-error"></p>
                <input type="hidden" name="${cachedFilePathName}" value="">
            </div>
            <button type="button" class="btn btn-danger btn-sm removeBadgeUpload">Remove</button>
        `;
        badgeUploadContainer.appendChild(newBadgeUpload);

        const badgeSelect = document.getElementById(badgeIdName);
        fetchAndPopulateBadgeDropdown(badgeSelect);

        newBadgeUpload.querySelector(".removeBadgeUpload").addEventListener("click", () => {
            badgeUploadContainer.removeChild(newBadgeUpload);
            updateAddBadgeButton();

            if (badgeUploadContainer.querySelectorAll(".badge-upload-unit").length === 0) {
                addBadgeUpload();
            }
        });

        updateAddBadgeButton();
    }

    // Initialize badge uploads
    if (badgeUploadContainer.querySelectorAll(".badge-upload-unit").length === 0) {
        addBadgeUpload();
    }

    addBadgeBtn.addEventListener("click", addBadgeUpload);

    updateAddBadgeButton();
});