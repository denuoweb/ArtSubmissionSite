function openBadgeModal() {
    const modal = document.getElementById('badgeModal');
    const modalBody = document.getElementById('badgeModalTableBody');

    // Clear existing rows
    modalBody.innerHTML = '';

    const basePath = document.querySelector('body').getAttribute('data-base-path') || "";

    // Fetch the badge data (use a server-side endpoint to provide the data)
    fetch(`${basePath}/api/badges`)
        .then(response => response.json())
        .then(data => {
            // Populate the modal with badge data
            data.forEach(badge => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="badge-name text-end" style="font-weight: bold; padding-right: 10px;">${badge.name}</td>
                    <td class="badge-description text-start" style="padding-left: 10px;">${badge.description}</td>
                `;
                modalBody.appendChild(row);
            });

            // Show the modal
            modal.style.display = 'block';
            modal.classList.add('show');
            document.body.classList.add('body-no-scroll'); // Prevent scrolling

            // Prevent background from scrolling
            document.body.style.overflow = 'hidden';
        
        })
        .catch(error => console.error('Error fetching badge data:', error));
}

function closeBadgeModal() {
    const modal = document.getElementById('badgeModal');

    // Hide the modal
    modal.style.display = 'none';
    modal.classList.remove('show');
    document.body.classList.remove('body-no-scroll'); // Restore scrolling

    // Restore background scrolling
    document.body.style.overflow = '';
}

function openTermsModal() {
    const modal = document.getElementById('termsModal');
    modal.style.display = 'block';
    modal.classList.add('show');

    // Prevent background from scrolling
    document.body.style.overflow = 'hidden';
}

function closeTermsModal() {
    const modal = document.getElementById('termsModal');
    modal.style.display = 'none';
    modal.classList.remove('show');

    // Restore background scrolling
    document.body.style.overflow = '';
}