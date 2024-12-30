// Updated form_validation.js (Preserves all existing logic and fixes the issue)

document.addEventListener("DOMContentLoaded", () => {
    const badgeUploadContainer = document.getElementById("badgeUploadContainer");
    const addBadgeUploadButton = document.getElementById("addBadgeUpload");

    if (!badgeUploadContainer || !addBadgeUploadButton) {
        console.error("Badge upload container or 'Add Another Badge' button is missing.");
        return;
    }

    // Add new badge upload functionality
    addBadgeUploadButton.addEventListener("click", () => {
        const badgeOptionsJSONElement = document.getElementById("badgeOptionsJSON");

        if (!badgeOptionsJSONElement) {
            console.error("Badge options JSON element not found.");
            return;
        }

        const badgeOptionsHTML = generateBadgeOptionsHTML(badgeOptionsJSONElement);

        if (!badgeOptionsHTML) {
            console.error("Badge options HTML could not be generated.");
            return;
        }

        const newBadgeUpload = document.createElement("fieldset");
        newBadgeUpload.classList.add("badge-upload-unit", "border", "p-3", "mb-3");
        newBadgeUpload.innerHTML = `
            <legend>Badge Upload</legend>
            <div class="mb-3">
                <label for="badge_id_new">Select a Badge</label>
                <select class="form-select" id="badge_id_new" name="badge_id_new" required>
                    <option value="" disabled selected>Select a badge</option>
                    ${badgeOptionsHTML}
                </select>
                <div class="invalid-feedback">Please select a badge.</div>
            </div>
            <div class="mb-3">
                <label for="artwork_file_new">Upload Artwork</label>
                <input type="file" class="form-control" id="artwork_file_new" name="artwork_file_new" accept="image/*" required>
                <div class="invalid-feedback">Please upload your artwork file.</div>
            </div>
            <button type="button" class="btn btn-danger btn-sm removeBadgeUpload">Remove</button>
        `;

        badgeUploadContainer.appendChild(newBadgeUpload);

        // Add remove functionality to the new badge upload
        const removeButton = newBadgeUpload.querySelector(".removeBadgeUpload");
        removeButton.addEventListener("click", () => {
            newBadgeUpload.remove();
        });

        // Add validation to the new file input
        const newFileInput = newBadgeUpload.querySelector("input[type='file']");
        if (newFileInput) {
            addFileSizeValidation(newFileInput);
        }
    });

    // Handle remove button clicks
    badgeUploadContainer.addEventListener("click", (event) => {
        if (event.target.classList.contains("removeBadgeUpload")) {
            event.target.closest(".badge-upload-unit").remove();
        }
    });

    // Add validation to all existing file inputs
    const existingFileInputs = document.querySelectorAll("input[type='file']");
    existingFileInputs.forEach((fileInput) => {
        addFileSizeValidation(fileInput);
    });

    // Form validation logic
    const form = document.getElementById("submissionForm");
    const submitButton = form?.querySelector('button[type="submit"]');

    if (!form || !submitButton) {
        console.error("Form or submit button not found!");
        return;
    }

    submitButton.disabled = true;

    form.addEventListener("input", () => {
        submitButton.disabled = !form.checkValidity();
    });

    form.addEventListener("input", (event) => {
        const field = event.target;
        validateField(field);
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const requiredFields = form.querySelectorAll("[required]");
        let allValid = true;

        requiredFields.forEach((field) => {
            if (!field.checkValidity()) {
                validateField(field);
                allValid = false;
            }
        });

        if (allValid) {
            console.log("All required fields are valid. Submitting form...");
            form.submit();
        }
    });

    // Email field real-time validation
    const emailField = document.getElementById("email");
    const emailErrorContainer = document.getElementById("email-error");

    let emailTimeout;

    emailField?.addEventListener("input", () => {
        clearTimeout(emailTimeout);

        emailTimeout = setTimeout(() => {
            const email = emailField.value.trim();
            if (!email) {
                showError(emailField, emailErrorContainer, "Email is required.");
                return;
            }

            clearError(emailField, emailErrorContainer);
            if (!isValidEmail(email)) {
                showError(emailField, emailErrorContainer, "Invalid email format.");
                return;
            }

            validateEmail(email);
        }, 500);
    });

    // Helper function to generate badge options HTML
    function generateBadgeOptionsHTML(badgeOptionsJSONElement) {
        try {
            const badgeData = JSON.parse(badgeOptionsJSONElement.textContent || "[]");

            if (!Array.isArray(badgeData) || badgeData.length === 0) {
                return null;
            }

            return badgeData
                .map(badge => `<option value="${badge.id}">${badge.name}: ${badge.description}</option>`)
                .join("");
        } catch (error) {
            console.error("Error parsing badge options JSON:", error);
            return null;
        }
    }

    // Helper function to validate file size
    function addFileSizeValidation(fileInput) {
        fileInput.addEventListener("change", () => {
            const files = fileInput.files;
            const maxFileSize = 8 * 1024 * 1024; // 8 MB in bytes

            if (files.length > 0) {
                const file = files[0];

                if (file.size > maxFileSize) {
                    const errorContainer = fileInput.nextElementSibling;
                    showError(
                        fileInput,
                        errorContainer,
                        `File size must not exceed 8 MB. Current size: ${(file.size / (1024 * 1024)).toFixed(2)} MB`
                    );
                    fileInput.value = ""; // Clear the file input to prevent invalid submission
                } else {
                    clearError(fileInput, fileInput.nextElementSibling);
                }
            }
        });
    }

    // Helper: Validate single field
    function validateField(field) {
        const fieldName = field.name || field.id;
        let errorContainer = document.getElementById(`${fieldName}-error`);

        if (!errorContainer) {
            errorContainer = createErrorContainer(field);
        }

        if (field.validity.valueMissing) {
            showError(field, errorContainer, `${fieldName} is required.`);
        } else if (field.validity.tooShort) {
            showError(field, errorContainer, `Too short: ${fieldName} requires at least ${field.minLength} characters.`);
        } else if (field.validity.tooLong) {
            showError(field, errorContainer, `Too long: ${fieldName} allows a maximum of ${field.maxLength} characters.`);
        } else if (field.validity.typeMismatch) {
            showError(field, errorContainer, `Invalid value for ${fieldName}.`);
        } else if (field.validity.patternMismatch) {
            showError(field, errorContainer, `Invalid format for ${fieldName}.`);
        } else {
            clearError(field, errorContainer);
        }
    }

    // Helper: Check if email format is valid
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Helper: Show error message
    function showError(field, errorContainer, message) {
        field.classList.add("is-invalid");
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = "block";
        }
    }

    // Helper: Clear error message
    function clearError(field, errorContainer) {
        field.classList.remove("is-invalid");
        if (errorContainer) {
            errorContainer.textContent = "";
            errorContainer.style.display = "none";
        }
    }

    // Helper: Email validation logic
    function validateEmail(email) {
        fetch("/validate_email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email })
        })
        .then((response) => response.json())
        .then((data) => {
            if (data.error) {
                showError(emailField, emailErrorContainer, data.error);
            } else {
                clearError(emailField, emailErrorContainer);
                emailErrorContainer.textContent = "Email is accepted.";
                emailErrorContainer.style.display = "block";
                emailErrorContainer.classList.add("text-success");
            }
        })
        .catch((error) => {
            console.error("Error validating email:", error);
            showError(emailField, emailErrorContainer, "An error occurred while validating the email.");
        });
    }

    function createErrorContainer(field) {
        const errorContainer = document.createElement("div");
        errorContainer.className = "invalid-feedback";
        errorContainer.id = `${field.name || field.id}-error`;

        if (field.parentNode) {
            field.parentNode.appendChild(errorContainer);
        } else {
            console.warn(`Parent node for field "${field.name || field.id}" not found.`);
        }

        return errorContainer;
    }
});
