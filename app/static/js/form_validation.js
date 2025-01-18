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

    // Validate email format
    function validateEmailFormat(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Check email availability
    async function checkEmailAvailability(email) {
        try {
            const csrfToken = document.querySelector('input[name="csrf_token"]').value;
            const response = await fetch("/api/check-email", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                throw new Error("Server error");
            }

            const result = await response.json();
            return result.isAvailable;
        } catch (error) {
            console.error("Error checking email availability:", error);
            return false;
        }
    }

    // Email field blur event
    emailField.addEventListener("blur", async () => {
        const email = emailField.value.trim();

        if (!validateEmailFormat(email)) {
            emailErrorContainer.textContent = "Invalid email format.";
            emailErrorContainer.style.display = "block";
            emailIsValid = false;
            return;
        }

        const isAvailable = await checkEmailAvailability(email);
        if (!isAvailable) {
            emailErrorContainer.textContent = "This email is already in use.";
            emailErrorContainer.style.display = "block";
            emailIsValid = false;
        } else {
            emailErrorContainer.textContent = "";
            emailErrorContainer.style.display = "none";
            emailIsValid = true;
        }
    });

    // File inputs with existing files
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

    // Update Add Badge button
    function updateAddBadgeButton() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        addBadgeBtn.disabled = currentUploads >= maxBadgeUploads;
        addBadgeBtn.style.display = currentUploads >= maxBadgeUploads ? "none" : "block";
    }

    // Populate dropdown
    function populateBadgeDropdown(selectElement, badgeData) {
        selectElement.innerHTML = '<option value="" disabled selected>Select a Badge</option>';
        badgeData.forEach(badge => {
            const option = document.createElement("option");
            option.value = badge.id;
            option.textContent = `${badge.name}: ${badge.description}`;
            selectElement.appendChild(option);
        });
    }

    // Add badge upload field
    function addBadgeUpload() {
        const currentUploads = badgeUploadContainer.querySelectorAll(".badge-upload-unit").length;
        if (currentUploads >= maxBadgeUploads) return;

        const index = currentUploads;
        const newBadgeUpload = document.createElement("fieldset");
        newBadgeUpload.classList.add("badge-upload-unit", "border", "p-3", "mb-3");

        const badgeIdName = `badge_uploads-${index}-badge_id`;
        const artworkFileName = `badge_uploads-${index}-artwork_file`;

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
            </div>
            <button type="button" class="btn btn-danger btn-sm removeBadgeUpload">Remove</button>
        `;
        badgeUploadContainer.appendChild(newBadgeUpload);

        const badgeSelect = document.getElementById(badgeIdName);
        fetch("/api/badges")
            .then(response => response.json())
            .then(badgeData => populateBadgeDropdown(badgeSelect, badgeData))
            .catch(error => console.error("Error fetching badges:", error));

        newBadgeUpload.querySelector(".removeBadgeUpload").addEventListener("click", () => {
            badgeUploadContainer.removeChild(newBadgeUpload);
            updateAddBadgeButton();

            // Ensure at least one badge upload is always present
            if (badgeUploadContainer.querySelectorAll(".badge-upload-unit").length === 0) {
                addBadgeUpload();
            }
        });

        updateAddBadgeButton();
    }

    // Automatically add the first badge upload section on page load
    if (badgeUploadContainer.querySelectorAll(".badge-upload-unit").length === 0) {
        addBadgeUpload();
    }

    // Attach click event to Add Badge button
    addBadgeBtn.addEventListener("click", addBadgeUpload);

    // Form submission handling
    form.addEventListener("submit", (event) => {
        let formIsValid = true;

        // Email validation
        if (!emailIsValid) {
            event.preventDefault();
            emailErrorContainer.textContent = "Please correct the email issues before submitting.";
            emailErrorContainer.style.display = "block";
            emailField.focus(); // Focus on the email field
            alert("Invalid email! Please fix the email before submitting."); // Optional: alert user
            formIsValid = false;
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
                if (formIsValid) field.focus(); // Focus on the first invalid field
                formIsValid = false;
            } else if (errorContainer) {
                errorContainer.textContent = "";
                errorContainer.style.display = "none";
            }
        });

        if (!formIsValid) {
            event.preventDefault();
        }
    });

    updateAddBadgeButton();
});
