/**
 * Lazy Load Critical Resources
 * Defers non-critical scripts for faster page load
 */

// Only load analytics and external scripts after page is fully loaded
window.addEventListener('load', function() {
    // Defer heavy third-party scripts
    const deferScripts = [
        // Add any third-party tracking scripts here if needed
    ];
    
    deferScripts.forEach(src => {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        document.body.appendChild(script);
    });
});

// Prefetch DNS for external resources
function prefetchDNS(url) {
    const link = document.createElement('link');
    link.rel = 'dns-prefetch';
    link.href = url;
    document.head.appendChild(link);
}

// Preconnect to critical origins
function preconnect(url) {
    const link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = url;
    document.head.appendChild(link);
}

// Preload critical fonts
function preloadFont(src, fontFamily) {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'font';
    link.href = src;
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);
}

// Load fonts
preloadFont('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap', 'Inter');
preloadFont('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&display=swap', 'Fira Code');
