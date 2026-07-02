function spawnParticles(x, y) {
    const colors = ['#3B82F6', '#60A5FA', '#93C5FD'];
    const count = 30;
    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        const size = Math.random() * 8 + 4;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];
        particle.style.position = 'fixed';
        particle.style.left = (x || window.innerWidth/2) + 'px';
        particle.style.top = (y || window.innerHeight/2) + 'px';
        particle.style.borderRadius = '50%';
        particle.style.pointerEvents = 'none';
        particle.style.zIndex = '9999';
        particle.style.transition = 'all 0.8s ease-out';
        document.body.appendChild(particle);
        const angle = Math.random() * Math.PI * 2;
        const velocity = Math.random() * 100 + 50;
        const dx = Math.cos(angle) * velocity;
        const dy = Math.sin(angle) * velocity - 50;
        setTimeout(() => {
            particle.style.transform = `translate(${dx}px, ${dy}px)`;
            particle.style.opacity = '0';
        }, 10);
        setTimeout(() => {
            particle.remove();
        }, 900);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const joinBtn = document.querySelector('a[href*="finish"]');
    if (joinBtn) {
        joinBtn.addEventListener('click', (e) => {
            const rect = joinBtn.getBoundingClientRect();
            spawnParticles(rect.left + rect.width/2, rect.top + rect.height/2);
        });
    }
});