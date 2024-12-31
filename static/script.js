// script.js
const translations = {};

// Function to load translations
async function loadTranslations(lang) {
    try {
        const response = await fetch(`/static/translations/${lang}.json`);
        if (!response.ok) {
            throw new Error(`Failed to load ${lang} translations`);
        }
        translations[lang] = await response.json();
        console.log(`Loaded translations for ${lang}:`, translations[lang]);
    } catch (error) {
        console.error(`Failed to load translations for ${lang}:`, error);
        // Fallback to English if translation fails
        if (lang !== 'en') {
            await loadTranslations('en');
        }
    }
}

// Function to translate the page
function translatePage(lang) {
    if (!translations[lang]) {
        console.error(`No translations available for ${lang}`);
        return;
    }

    // Handle RTL languages
    const rtlLanguages = ['ar', 'fa', 'he'];
    document.documentElement.dir = rtlLanguages.includes(lang) ? 'rtl' : 'ltr';

    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            if (element.tagName === 'INPUT' && element.getAttribute('placeholder')) {
                element.placeholder = translations[lang][key];
            } else {
                element.textContent = translations[lang][key];
            }
        }
    });

    document.documentElement.lang = lang;
}

// Update the changeLanguage function
async function changeLanguage(lang) {
    if (!translations[lang]) {
        await loadTranslations(lang);
    }
    translatePage(lang);
    
    // Save language preference
    localStorage.setItem('preferred_language', lang);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Get user's preferred language
    const savedLang = localStorage.getItem('preferred_language');
    const browserLang = navigator.language.split('-')[0];
    const defaultLang = savedLang || browserLang || 'en';
    
    // Load and apply translations
    await loadTranslations(defaultLang);
    translatePage(defaultLang);
    
    // Set the language selector value
    const langSelect = document.getElementById('language-select');
    if (langSelect) {
        langSelect.value = defaultLang;
    }
});

async function updateProgress(progress) {
    $("#progress-container").show();
    $("#progress-bar").css("width", progress + "%");
    $("#progress-bar").attr("aria-valuenow", progress);
    $("#progress-text").text(`Downloading: ${progress}%`);
}

async function showError(message) {
    $("#progress-container").hide();
    alert(message);
}

async function getVideoInfo(url) {
    try {
        const response = await fetch("/video-info", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url: url }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail);
        }

        const data = await response.json();
        $("#video-info").show();
        $("#video-title").text(data.title);
        $("#video-duration").text(data.duration);
        $("#video-quality").text(data.format);
        return data;
    } catch (error) {
        showError(error.message);
        throw error;
    }
}

// Add error handling utility
const handleError = (error) => {
    showError(error?.message || "An unexpected error occurred");
    console.error(error);
};

async function downloadVideo() {
    const url = $("#url").val().trim();
    
    if (!url) {
        handleError(new Error("Please enter a valid URL"));
        return;
    }

    try {
        await getVideoInfo(url);
        const response = await fetch("/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            throw new Error((await response.json()).detail);
        }

        const data = await response.json();
        data.progress ? 
            await updateProgress(parseFloat(data.progress)) :
            showError(data.message);
    } catch (error) {
        handleError(error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Clipboard functionality
    const input = document.querySelector('.search-form__input');
    const pasteBtn = document.querySelector('.paste-btn');

    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            input.value = text;
        } catch (err) {
            console.error('Failed to read clipboard:', err);
        }
    });

    // Function to handle section visibility and URL updates
    function showSection(sectionId) {
        // Hide all sections first
        document.querySelectorAll('.contact-section, .privacy-section, .terms-section').forEach(section => {
            section.style.display = 'none';
        });

        // Show the requested section
        const section = document.getElementById(sectionId);
        if (section) {
            section.style.display = 'block';
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // Update URL without reloading the page
            history.pushState(null, '', `#${sectionId}`);
        }
    }

    // Add handlers for feature links
    const featureLinks = document.querySelectorAll('.footer__links-group:first-child .footer-link');
    
    featureLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const featureType = link.textContent.trim();
            
            // Update URL with feature type
            history.pushState(null, '', `#${featureType.toLowerCase().replace(' ', '-')}`);
            
            // Scroll to form section
            const formSection = document.querySelector('.form-block');
            formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Update input placeholder
            const input = document.querySelector('.search-form__input');
            input.placeholder = `Paste your ${featureType.toLowerCase()} URL here`;
        });
    });

    // Add click handlers for footer links
    const footerLinks = {
        'contact-section': document.querySelector('a[href="#contact-section"]'),
        'privacy-section': document.querySelector('a[href="#privacy-section"]'),
        'terms-section': document.querySelector('a[href="#terms-section"]')
    };

    Object.entries(footerLinks).forEach(([sectionId, link]) => {
        if (link) {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                showSection(sectionId);
            });
        }
    });

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function() {
        const hash = window.location.hash.slice(1);
        if (hash) {
            if (['contact-section', 'privacy-section', 'terms-section'].includes(hash)) {
                showSection(hash);
            } else {
                // For feature links, scroll to form
                const formSection = document.querySelector('.form-block');
                formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    });

    // Handle initial page load with hash
    if (window.location.hash) {
        const hash = window.location.hash.slice(1);
        if (['contact-section', 'privacy-section', 'terms-section'].includes(hash)) {
            showSection(hash);
        }
    }

    // Add to your existing DOMContentLoaded event listener
    document.querySelectorAll('.faq-question').forEach(button => {
        button.addEventListener('click', () => {
            const faqItem = button.parentElement;
            const isActive = faqItem.classList.contains('active');
            
            // Close all FAQ items
            document.querySelectorAll('.faq-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Open clicked item if it wasn't active
            if (!isActive) {
                faqItem.classList.add('active');
            }
        });
    });

    // Language selector dropdown
    const langBtn = document.getElementById('language-select-btn');
    const langDropdown = document.getElementById('language-dropdown');
    
    langBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        langDropdown.style.display = langDropdown.style.display === 'none' ? 'block' : 'none';
    });
    
    document.addEventListener('click', (e) => {
        if (!langDropdown.contains(e.target)) {
            langDropdown.style.display = 'none';
        }
    });

    // Update current language text when language changes
    const updateCurrentLanguage = (lang) => {
        const langName = document.querySelector(`.language-option[onclick*="${lang}"] span`).textContent;
        document.getElementById('current-language').textContent = langName;
    };
});

