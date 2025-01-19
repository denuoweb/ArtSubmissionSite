document.addEventListener("DOMContentLoaded", function() {
    const csrfTokenInput = document.querySelector('input[name="csrf_token"]');

    function refreshCsrfToken() {
        fetch(`${basePath}/refresh_csrf`)
            .then(response => response.json())
            .then(data => {
                if (data.csrf_token) {
                    csrfTokenInput.value = data.csrf_token;
                    // Update the CSRF token in AJAX setup if needed
                    updateAjaxCsrfToken(data.csrf_token);
                }
            })
            .catch(error => console.error('Error refreshing CSRF token:', error));
    }

    function updateAjaxCsrfToken(csrfToken) {
        // Assuming you are using fetch API for AJAX
        document.querySelectorAll("fetch, ajax").forEach(call => {
            call.headers['X-CSRFToken'] = csrfToken;
        });
    }

    // Set CSRF token to refresh every 15 minutes
    setInterval(refreshCsrfToken, 900000);  // 900000 milliseconds = 15 minutes
});

