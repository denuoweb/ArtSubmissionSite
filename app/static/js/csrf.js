// static/js/csrf.js

document.addEventListener("DOMContentLoaded", function() {
    const csrfMetaTag = document.querySelector('meta[name="csrf-token"]');
    const csrfHiddenInput = document.querySelector('input[name="csrf_token"]');
    const basePath = document.querySelector('body').getAttribute('data-base-path') || "";

    function refreshCsrfToken() {
        fetch(`${basePath}/refresh_csrf`, {
            method: 'GET',
            credentials: 'same-origin' // Ensure cookies are sent if needed
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.csrf_token) {
                // Update the meta tag
                if (csrfMetaTag) {
                    csrfMetaTag.setAttribute('content', data.csrf_token);
                    console.log("CSRF token refreshed via meta tag.");
                } else {
                    console.error("CSRF meta tag not found.");
                }

                // Update the hidden input in the form
                if (csrfHiddenInput) {
                    csrfHiddenInput.value = data.csrf_token;
                    console.log("CSRF token updated in hidden input.");
                } else {
                    console.error("CSRF hidden input not found in the form.");
                }
            } else {
                console.error("CSRF token not found in the response.");
            }
        })
        .catch(error => console.error('Error refreshing CSRF token:', error));
    }

    // Refresh CSRF token every 15 minutes (900,000 milliseconds)
    setInterval(refreshCsrfToken, 900000);

    // Initial CSRF token refresh on page load
    refreshCsrfToken();
});
