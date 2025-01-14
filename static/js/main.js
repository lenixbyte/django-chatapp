// Handle responsive menu toggle
function toggleMenu() {
    const leftMenu = document.getElementById('leftMenu');
    if (leftMenu) {
        leftMenu.classList.toggle('active');
    }
}

// Handle responsive page scaling
function handleResponsiveScaling() {
    const width = window.innerWidth;
    const html = document.documentElement;

    if (width >= 992 && width <= 1600) {
        html.style.zoom = '0.9';
    } else if (width >= 700 && width <= 767) {
        html.style.zoom = '0.8';
    } else if (width >= 600 && width <= 700) {
        html.style.zoom = '0.75';
    } else if (width <= 600) {
        html.style.zoom = '0.5';
    } else {
        html.style.zoom = '1';
    }
}

// Initialize responsive behavior
// window.addEventListener('load', handleResponsiveScaling);
// window.addEventListener('resize', handleResponsiveScaling);

// Close menu when clicking outside on mobile
document.addEventListener('click', (event) => {
    const leftMenu = document.getElementById('leftMenu');
    const toggleButton = document.querySelector('.toggle-menu');
    
    if (leftMenu && toggleButton) {
        if (!leftMenu.contains(event.target) && !toggleButton.contains(event.target)) {
            leftMenu.classList.remove('active');
        }
    }
});

function toggleTheme() {
    const html = document.documentElement;
    const themeToggle = document.querySelector('.theme-toggle');
    const themeIcon = themeToggle.querySelector('i');
    const themeText = themeToggle.querySelector('.theme-text');
    
    if (html.getAttribute('data-theme') === 'light') {
        html.setAttribute('data-theme', 'dark');
        themeIcon.className = 'fas fa-moon';
        themeText.textContent = 'Dark';
        localStorage.setItem('theme', 'dark');
    } else {
        html.setAttribute('data-theme', 'light');
        themeIcon.className = 'fas fa-sun';
        themeText.textContent = 'Light';
        localStorage.setItem('theme', 'light');
    }
}

// Set initial theme from localStorage
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        const themeIcon = themeToggle.querySelector('i');
        const themeText = themeToggle.querySelector('.theme-text');
        
        if (savedTheme === 'light') {
            themeIcon.className = 'fas fa-sun';
            themeText.textContent = 'Light';
        }
    }
});

// Sidebar toggle functionality
document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('toggleSidebar');
    const closeBtn = document.getElementById('closeSidebar');
    const sidebar = document.getElementById('sidebar');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.add('active');
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            sidebar.classList.remove('active');
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (event) => {
        if (window.innerWidth <= 768) {
            if (!sidebar.contains(event.target) && 
                !toggleBtn.contains(event.target) && 
                sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
            }
        }
    });
}); 