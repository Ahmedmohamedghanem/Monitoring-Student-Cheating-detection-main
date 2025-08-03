async function toggleCamera(mode) {
    try {
        const response = await fetch(/toggle_camera/${mode}/, { method: 'POST' });
        const data = await response.json();
        alert(data.status || data.error);
    } catch (error) {
        console.error('Error toggling camera:', error);
    }
}

async function releaseCamera() {
    try {
        const response = await fetch('/release_camera/', { method: 'POST' });
        const data = await response.json();
        alert(data.status || data.error);
    } catch (error) {
        console.error('Error releasing camera:', error);
    }
}

async function uploadVideo(fileInputId) {
    const input = document.getElementById(fileInputId);
    if (input.files.length === 0) {
        alert('Please select a video file.');
        return;
    }

    const formData = new FormData();
    formData.append('video', input.files[0]);

    try {
        const response = await fetch('/upload_video/', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        alert(data.status || data.error);
    } catch (error) {
        console.error('Error uploading video:', error);
    }
}

async function listVideos(containerId) {
    try {
        const response = await fetch('/list_uploaded_videos/');
        const data = await response.json();
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (data.videos) {
            data.videos.forEach(video => {
                const videoElement = document.createElement('div');
                videoElement.innerHTML = <a href="/static/videos/${video}" target="_blank">${video}</a>;
                container.appendChild(videoElement);
            });
        } else {
            container.innerHTML = 'No videos found.';
        }
    } catch (error) {
        console.error('Error listing videos:', error);
    }
}