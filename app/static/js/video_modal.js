function openVideoModal() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('informationalVideo');

    // Show the modal
    modal.style.display = 'block';
    modal.classList.add('show');

    // Play the video when the modal opens
    video.play();

    // Prevent background from scrolling
    document.body.style.overflow = 'hidden';
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

    // Restore background scrolling
    document.body.style.overflow = '';
}
