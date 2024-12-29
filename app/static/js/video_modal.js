function openVideoModal() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('informationalVideo');

    // Show the modal
    modal.style.display = 'block';
    modal.classList.add('show');

    // Play the video when the modal opens
    video.play();
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('informationalVideo');

    // Pause the video and reset it when the modal closes
    video.pause();
    video.currentTime = 0;

    // Hide the modal
    modal.style.display = 'none';
    modal.classList.remove('show');
}
