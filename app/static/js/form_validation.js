document.addEventListener("DOMContentLoaded", () => {
    // Badge upload logic
    document.getElementById("addBadgeUpload").addEventListener("click", () => {
        const badgeUploadContainer = document.getElementById("badgeUploadContainer");
        const newBadgeUpload = badgeUploadContainer.querySelector(".badge-upload-unit").cloneNode(true);

        // Clear cloned fields
        const selectField = newBadgeUpload.querySelector("select");
        const fileField = newBadgeUpload.querySelector("input[type='file']");
        const errorContainer = newBadgeUpload.querySelector(".invalid-feedback");

        selectField.value = ""; // Reset dropdown
        fileField.value = ""; // Reset file input
        errorContainer.textContent = ""; // Clear error messages

        selectField.classList.remove("is-invalid");
        fileField.classList.remove("is-invalid");

        badgeUploadContainer.appendChild(newBadgeUpload);
    });

    // Form validation logic
    const form = document.getElementById("submissionForm");
    const submitButton = form.querySelector('button[type="submit"]');

    // Exit if form or submit button is not found
    if (!form || !submitButton) {
        console.error("Form or submit button not found!");
        return;
    }

    // Disable the submit button initially
    submitButton.disabled = true;

    // Enable submit button when the form is valid
    form.addEventListener("input", () => {
        if (form.checkValidity()) {
            submitButton.disabled = false;
        } else {
            submitButton.disabled = true;
        }
    });

    // Real-time validation for each required field
    form.addEventListener("input", (event) => {
        const field = event.target;
        validateField(field);
    });

    // Validate all fields on form submission
    form.addEventListener("submit", (event) => {
        event.preventDefault(); // Prevent default submission for debugging

        const requiredFields = form.querySelectorAll("[required]");
        let allValid = true;

        requiredFields.forEach((field) => {
            if (!field.checkValidity()) {
                validateField(field); // Re-validate each field
                allValid = false;
            }
        });

        if (allValid) {
            console.log("All required fields are valid. Submitting form...");
            form.submit(); // Submit manually if all fields are valid
        }
    });

    // Email field real-time validation
    const emailField = document.getElementById("email");
    const emailErrorContainer = document.getElementById("email-error");

    // Add a debounce function to limit the number of requests
    let emailTimeout;

    emailField.addEventListener("input", () => {
        clearTimeout(emailTimeout);

        // Perform email validation after the user stops typing for 500ms
        emailTimeout = setTimeout(() => {
            const email = emailField.value.trim();
            if (!email) {
                showError(emailField, emailErrorContainer, "Email is required.");
                return;
            }

            // Clear any previous errors and validate the format
            clearError(emailField, emailErrorContainer);
            if (!isValidEmail(email)) {
                showError(emailField, emailErrorContainer, "Invalid email format.");
                return;
            }

            // Make AJAX request to validate the email
            validateEmail(email);
        }, 500); // 500ms debounce
    });

    // Real-time validation logic for fields
    function validateField(field) {
        const fieldName = field.name || field.id;
        let errorContainer = document.getElementById(`${fieldName}-error`);

        // Fallback if error container is missing
        if (!errorContainer) {
            console.warn(`Error container for "${fieldName}" not found.`);
            errorContainer = createErrorContainer(field); // Create one dynamically
        }

        // Validation logic
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

    // Email validation with AJAX
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
                emailErrorContainer.classList.add("text-success"); // Optional success styling
            }
        })
        .catch((error) => {
            console.error("Error validating email:", error);
            showError(emailField, emailErrorContainer, "An error occurred while validating the email.");
        });
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Show error message
    function showError(field, errorContainer, message) {
        field.classList.add("is-invalid");
        errorContainer.textContent = message;
        errorContainer.style.display = "block"; // Ensure the error container is visible
        errorContainer.classList.remove("text-success");
    }

    // Clear error message
    function clearError(field, errorContainer) {
        field.classList.remove("is-invalid");
        errorContainer.textContent = "";
        errorContainer.style.display = "none"; // Hide the error container
        errorContainer.classList.remove("text-success");
    }

    // Dynamically create an error container if it doesn't exist
    function createErrorContainer(field) {
        const errorContainer = document.createElement("div");
        errorContainer.className = "invalid-feedback"; // Add Bootstrap styling for invalid feedback
        errorContainer.id = `${field.name || field.id}-error`; // Set a unique ID for the error container

        // Append the error container right after the field
        if (field.parentNode) {
            field.parentNode.appendChild(errorContainer);
        } else {
            console.warn(`Parent node for field "${field.name || field.id}" not found.`);
        }

        return errorContainer;
    }
});
