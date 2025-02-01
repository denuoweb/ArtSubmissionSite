// static/js/youth_form_validation.js

document.addEventListener("DOMContentLoaded", () => {

    // -------------------------
    // Configuration and Element Selection
    // -------------------------
    const basePath = window.basePath || ''; // Ensure basePath is defined if used
    const form = document.getElementById("youthSubmissionForm");
    
    // Selecting form fields by their IDs
    const nameField = document.getElementById("youth_name");
    const nameError = document.getElementById("name-error");

    const ageField = document.getElementById("youth_age");
    const ageError = document.getElementById("age-error");

    const parentContactField = document.getElementById("youth_parent_contact_info");
    const parentContactError = document.getElementById("parent_contact_info-error");

    const emailField = document.getElementById("youth_email");
    const emailError = document.getElementById("email-error");

    const aboutWhyDesignField = document.getElementById("youth_about_why_design");
    const aboutWhyDesignError = document.getElementById("about_why_design-error");

    const aboutYourselfField = document.getElementById("youth_about_yourself");
    const aboutYourselfError = document.getElementById("about_yourself-error");

    const badgeSelect = document.getElementById("youth_badge_id");
    const badgeError = document.getElementById("badge_id-error");

    const artworkFileField = document.getElementById("youth_artwork_file");
    const artworkFileError = document.getElementById("youth_artwork_file-error");

    const parentConsentField = document.getElementById("youth_parent_consent");
    const parentConsentError = document.getElementById("parent_consent-error");

    const submitButton = form.querySelector('button[type="submit"]');

    // -------------------------
    // Helper Functions
    // -------------------------

    // Function to validate email format
    function validateEmailFormat(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    async function checkEmailAvailability(email) {
        try {
            // Retrieve CSRF token from meta tag
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            const basePath = document.querySelector('body').getAttribute('data-base-path') || "";

            const response = await fetch(`${basePath}/api/check-youth-email`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ email, type: "youth" }), // Specify type if needed
            });

            const result = await response.json();

            if (!response.ok) {
                if (result.error === "CSRF token missing or invalid.") {
                    alert("Session expired. Please refresh the page and try again.");
                } else {
                    console.error(`Server returned ${response.status}: ${response.statusText}`);
                    throw new Error(result.error || "Server error");
                }
            }

            return result.isAvailable;
        } catch (error) {
            console.error("Error checking email availability:", error.message);
            alert("Unable to verify email at this time. Please try again later.");
            return false; // Assume email is unavailable if an error occurs
        }
    }

    // Function to validate artwork file
    function validateArtworkFile() {
        if (!artworkFileField) return true; // If artwork file field is not present, skip validation

        const file = artworkFileField.files[0];
        const existingFilePath = artworkFileField.getAttribute('data-existing');

        // If there's an existing file and no new file is uploaded, it's valid
        if (existingFilePath && !file) {
            artworkFileError.textContent = "";
            artworkFileError.style.display = "none";
            artworkFileField.classList.remove("is-invalid");
            artworkFileField.classList.add("is-valid");
            return true;
        }

        // If no existing file and no new file, invalid
        if (!existingFilePath && !file) {
            artworkFileError.textContent = "Please upload your artwork file.";
            artworkFileError.style.display = "block";
            artworkFileField.classList.add("is-invalid");
            artworkFileField.classList.remove("is-valid");
            return false;
        }

        // Validate file type
        const allowedExtensions = ['jpg', 'jpeg', 'png', 'svg'];
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!allowedExtensions.includes(fileExtension)) {
            artworkFileError.textContent = "Only JPG, JPEG, PNG, or SVG files are allowed.";
            artworkFileError.style.display = "block";
            artworkFileField.classList.add("is-invalid");
            artworkFileField.classList.remove("is-valid");
            return false;
        }

        // Validate file size (max 8 MB)
        const maxSizeMB = 8;
        const fileSizeMB = file.size / (1024 * 1024);
        if (fileSizeMB > maxSizeMB) {
            artworkFileError.textContent = `File size must not exceed ${maxSizeMB} MB.`;
            artworkFileError.style.display = "block";
            artworkFileField.classList.add("is-invalid");
            artworkFileField.classList.remove("is-valid");
            return false;
        }

        // If valid
        artworkFileError.textContent = "";
        artworkFileError.style.display = "none";
        artworkFileField.classList.remove("is-invalid");
        artworkFileField.classList.add("is-valid");
        return true;
    }

    // Function to validate parent consent
    function validateParentConsent() {
        if (parentConsentField.checked) {
            parentConsentError.textContent = "";
            parentConsentError.style.display = "none";
            parentConsentField.classList.remove("is-invalid");
            parentConsentField.classList.add("is-valid");
            return true;
        } else {
            parentConsentError.textContent = "Parent/Guardian consent is required.";
            parentConsentError.style.display = "block";
            parentConsentField.classList.add("is-invalid");
            parentConsentField.classList.remove("is-valid");
            return false;
        }
    }

    // -------------------------
    // Validation Functions for Each Field
    // -------------------------

    async function validateName() {
        const name = nameField.value.trim();
        if (name === "") {
            nameError.textContent = "Your name is required.";
            nameError.style.display = "block";
            nameField.classList.add("is-invalid");
            nameField.classList.remove("is-valid");
            return false;
        } else if (name.length > 100) {
            nameError.textContent = "Name cannot exceed 100 characters.";
            nameError.style.display = "block";
            nameField.classList.add("is-invalid");
            nameField.classList.remove("is-valid");
            return false;
        } else {
            nameError.textContent = "";
            nameError.style.display = "none";
            nameField.classList.remove("is-invalid");
            nameField.classList.add("is-valid");
            return true;
        }
    }

    async function validateAge() {
        const age = parseInt(ageField.value, 10);
        if (isNaN(age)) {
            ageError.textContent = "Your age is required.";
            ageError.style.display = "block";
            ageField.classList.add("is-invalid");
            ageField.classList.remove("is-valid");
            return false;
        } else if (age < 13 || age > 18) {
            ageError.textContent = "Age must be between 13 and 18.";
            ageError.style.display = "block";
            ageField.classList.add("is-invalid");
            ageField.classList.remove("is-valid");
            return false;
        } else {
            ageError.textContent = "";
            ageError.style.display = "none";
            ageField.classList.remove("is-invalid");
            ageField.classList.add("is-valid");
            return true;
        }
    }

    async function validateParentContact() {
        const contact = parentContactField.value.trim();
        if (contact === "") {
            parentContactError.textContent = "Parent/Guardian contact information is required.";
            parentContactError.style.display = "block";
            parentContactField.classList.add("is-invalid");
            parentContactField.classList.remove("is-valid");
            return false;
        } else if (contact.length > 300) {
            parentContactError.textContent = "Contact information cannot exceed 300 characters.";
            parentContactError.style.display = "block";
            parentContactField.classList.add("is-invalid");
            parentContactField.classList.remove("is-valid");
            return false;
        } else {
            parentContactError.textContent = "";
            parentContactError.style.display = "none";
            parentContactField.classList.remove("is-invalid");
            parentContactField.classList.add("is-valid");
            return true;
        }
    }

    async function validateEmail() {
        const email = emailField.value.trim();

        // Validate email format
        if (!validateEmailFormat(email)) {
            emailError.textContent = "Please provide a valid email address.";
            emailError.style.display = "block";
            emailField.classList.add("is-invalid");
            emailField.classList.remove("is-valid");
            return false;
        }

        // Check email availability
        const isAvailable = await checkEmailAvailability(email);
        if (!isAvailable) {
            emailError.textContent = "This email is already in use.";
            emailError.style.display = "block";
            emailField.classList.add("is-invalid");
            emailField.classList.remove("is-valid");
            return false;
        } else {
            emailError.textContent = "";
            emailError.style.display = "none";
            emailField.classList.remove("is-invalid");
            emailField.classList.add("is-valid");
            return true;
        }
    }

    async function validateAboutWhyDesign() {
        const text = aboutWhyDesignField.value.trim();
        if (text === "") {
            aboutWhyDesignError.textContent = "This field is required.";
            aboutWhyDesignError.style.display = "block";
            aboutWhyDesignField.classList.add("is-invalid");
            aboutWhyDesignField.classList.remove("is-valid");
            return false;
        } else if (text.length > 500) {
            aboutWhyDesignError.textContent = "Response cannot exceed 500 characters.";
            aboutWhyDesignError.style.display = "block";
            aboutWhyDesignField.classList.add("is-invalid");
            aboutWhyDesignField.classList.remove("is-valid");
            return false;
        } else {
            aboutWhyDesignError.textContent = "";
            aboutWhyDesignError.style.display = "none";
            aboutWhyDesignField.classList.remove("is-invalid");
            aboutWhyDesignField.classList.add("is-valid");
            return true;
        }
    }

    async function validateAboutYourself() {
        const text = aboutYourselfField.value.trim();
        if (text === "") {
            aboutYourselfError.textContent = "This field is required.";
            aboutYourselfError.style.display = "block";
            aboutYourselfField.classList.add("is-invalid");
            aboutYourselfField.classList.remove("is-valid");
            return false;
        } else if (text.length > 500) {
            aboutYourselfError.textContent = "Response cannot exceed 500 characters.";
            aboutYourselfError.style.display = "block";
            aboutYourselfField.classList.add("is-invalid");
            aboutYourselfField.classList.remove("is-valid");
            return false;
        } else {
            aboutYourselfError.textContent = "";
            aboutYourselfError.style.display = "none";
            aboutYourselfField.classList.remove("is-invalid");
            aboutYourselfField.classList.add("is-valid");
            return true;
        }
    }

    async function validateBadgeSelection() {
        const badgeId = parseInt(badgeSelect.value, 10);
        if (isNaN(badgeId) || badgeId === 0) { // Assuming "0" is the value for "Select a Badge"
            badgeError.textContent = "Please select a badge.";
            badgeError.style.display = "block";
            badgeSelect.classList.add("is-invalid");
            badgeSelect.classList.remove("is-valid");
            return false;
        } else {
            badgeError.textContent = "";
            badgeError.style.display = "none";
            badgeSelect.classList.remove("is-invalid");
            badgeSelect.classList.add("is-valid");
            return true;
        }
    }

    // -------------------------
    // Event Listeners for Validation
    // -------------------------

    nameField.addEventListener("blur", validateName);
    nameField.addEventListener("input", validateName);

    ageField.addEventListener("blur", validateAge);
    ageField.addEventListener("input", validateAge);

    parentContactField.addEventListener("blur", validateParentContact);
    parentContactField.addEventListener("input", validateParentContact);

    emailField.addEventListener("blur", validateEmail);
    emailField.addEventListener("input", validateEmail);

    aboutWhyDesignField.addEventListener("blur", validateAboutWhyDesign);
    aboutWhyDesignField.addEventListener("input", validateAboutWhyDesign);

    aboutYourselfField.addEventListener("blur", validateAboutYourself);
    aboutYourselfField.addEventListener("input", validateAboutYourself);

    badgeSelect.addEventListener("change", validateBadgeSelection);

    artworkFileField.addEventListener("change", validateArtworkFile);

    parentConsentField.addEventListener("change", validateParentConsent);

    // -------------------------
    // Form Submission Handling
    // -------------------------
    form.addEventListener("submit", async (event) => {
        // Prevent form submission to perform validations
        event.preventDefault();

        // Perform all validations
        const isNameValid = await validateName();
        const isAgeValid = await validateAge();
        const isParentContactValid = await validateParentContact();
        const isEmailValid = await validateEmail();
        const isAboutWhyDesignValid = await validateAboutWhyDesign();
        const isAboutYourselfValid = await validateAboutYourself();
        const isBadgeValid = await validateBadgeSelection();
        const isArtworkValid = validateArtworkFile();
        const isParentConsentValid = validateParentConsent();

        // Check if all validations passed
        if (
            isNameValid &&
            isAgeValid &&
            isParentContactValid &&
            isEmailValid &&
            isAboutWhyDesignValid &&
            isAboutYourselfValid &&
            isBadgeValid &&
            isArtworkValid &&
            isParentConsentValid
        ) {
            // All validations passed, submit the form
            form.submit();
        } else {
            // Scroll to the first error for better user experience
            const firstError = form.querySelector(".is-invalid");
            if (firstError) {
                firstError.scrollIntoView({ behavior: "smooth", block: "center" });
                firstError.focus();
            }

            // Display a general error message if not already present
            const generalError = document.getElementById("general-error");
            if (!generalError) {
                const errorDiv = document.createElement("div");
                errorDiv.className = "alert alert-danger mt-3";
                errorDiv.id = "general-error";
                errorDiv.textContent = "Please correct the errors in the form.";
                form.appendChild(errorDiv);
            }
        }
    });

});
