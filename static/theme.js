(function() {
    const html = document.documentElement;
    const toggleBtns = document.querySelectorAll('#theme-toggle, #theme-toggle-mobile');

    function getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('dropshop-theme', theme);
        const icon = theme === 'dark' ? '☀️' : '🌙';
        toggleBtns.forEach(btn => btn.textContent = icon);
    }

    // Инициализация
    const saved = localStorage.getItem('dropshop-theme');
    if (saved) {
        setTheme(saved);
    } else {
        setTheme(getSystemTheme());
    }

    // Переключение по клику
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const current = html.getAttribute('data-theme');
            setTheme(current === 'dark' ? 'light' : 'dark');
        });
    });

    // Автосмена темы, если изменились настройки системы (без перезагрузки)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('dropshop-theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
})();