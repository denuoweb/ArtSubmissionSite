// static/js/csrf.js

document.addEventListener("DOMContentLoaded", function() {
    const csrfMetaTag = document.querySelector('meta[name="csrf-token"]');

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
            if (data.csrf_token && csrfMetaTag) {
                csrfMetaTag.setAttribute('content', data.csrf_token);
                console.log("CSRF token refreshed via meta tag.");
            } else {
                console.error("CSRF token not found in response or meta tag missing.");
            }
        })
        .catch(error => console.error('Error refreshing CSRF token:', error));
    }

    // Set CSRF token to refresh every 15 minutes (900,000 milliseconds)
    setInterval(refreshCsrfToken, 900000);

    // Initial CSRF token refresh on page load
    refreshCsrfToken();
});
