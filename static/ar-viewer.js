let currentImage = '';
let videoStream = null;

function openAR(imageUrl) {
    currentImage = imageUrl;
    document.getElementById('ar-overlay').src = imageUrl;
    document.getElementById('ar-modal').classList.remove('hidden');
    startCamera();
}

function closeAR() {
    document.getElementById('ar-modal').classList.add('hidden');
    stopCamera();
}

async function startCamera() {
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        const video = document.getElementById('ar-video');
        video.srcObject = videoStream;
    } catch(e) {
        alert('Не удалось получить доступ к камере. Убедитесь, что вы используете HTTPS и разрешили доступ.');
        closeAR();
    }
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
}

function capturePhoto() {
    const video = document.getElementById('ar-video');
    const canvas = document.getElementById('ar-canvas');
    const overlay = document.getElementById('ar-overlay');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
    ctx.restore();
    // Рисуем наложение
    const overlayRect = overlay.getBoundingClientRect();
    const videoRect = video.getBoundingClientRect();
    const scaleX = canvas.width / videoRect.width;
    const scaleY = canvas.height / videoRect.height;
    const x = (overlayRect.left - videoRect.left) * scaleX;
    const y = (overlayRect.top - videoRect.top) * scaleY;
    const w = overlayRect.width * scaleX;
    const h = overlayRect.height * scaleY;
    const img = new Image();
    img.src = currentImage;
    img.onload = () => {
        ctx.drawImage(img, x, y, w, h);
        const dataUrl = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = 'dropshop-ar-photo.png';
        link.click();
    };
}

// Перетаскивание наложения
(function() {
    const overlay = document.getElementById('ar-overlay');
    let isDragging = false;
    let startX, startY, initialLeft, initialTop;
    overlay.addEventListener('touchstart', (e) => {
        isDragging = true;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        const rect = overlay.getBoundingClientRect();
        initialLeft = rect.left;
        initialTop = rect.top;
        e.preventDefault();
    });
    window.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        const dx = e.touches[0].clientX - startX;
        const dy = e.touches[0].clientY - startY;
        overlay.style.left = `${initialLeft + dx}px`;
        overlay.style.top = `${initialTop + dy}px`;
        overlay.style.transform = 'none';
    });
    window.addEventListener('touchend', () => {
        isDragging = false;
    });
})();