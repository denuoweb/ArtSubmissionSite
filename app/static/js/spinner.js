// In a separate JS file or within your existing scripts
document.addEventListener("DOMContentLoaded", () => {
    const forms = document.querySelectorAll("form");

    forms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            // Show global spinner
            const globalSpinner = document.getElementById("globalSpinner");
            globalSpinner.classList.remove("d-none");
        });
    });
});
