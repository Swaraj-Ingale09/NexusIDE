/**
 * Frontend Performance Optimizations
 */

// 1. Debounce function for high-frequency events
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 2. Throttle function for scroll/resize events
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 3. Lazy load images
document.addEventListener('DOMContentLoaded', function() {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.removeAttribute('loading');
                    observer.unobserve(img);
                }
            });
        });
        lazyImages.forEach(img => imageObserver.observe(img));
    }
});

// 4. RequestAnimationFrame for smooth animations
function smoothScroll(target, duration = 300) {
    const start = window.scrollY;
    const startTime = performance.now();
    
    function scroll(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        window.scrollTo(0, start + (target - start) * easeInOutQuad(progress));
        
        if (progress < 1) {
            requestAnimationFrame(scroll);
        }
    }
    
    function easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }
    
    requestAnimationFrame(scroll);
}

// 5. API Request Caching
class APICache {
    constructor(ttl = 300000) {  // 5 minutes default
        this.cache = new Map();
        this.ttl = ttl;
    }
    
    async fetch(url, options = {}) {
        const cacheKey = `${url}:${JSON.stringify(options)}`;
        
        // Check cache
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.time < this.ttl) {
                return cached.data;
            }
        }
        
        // Fetch and cache
        const response = await fetch(url, options);
        const data = await response.json();
        
        this.cache.set(cacheKey, {
            data: data,
            time: Date.now()
        });
        
        return data;
    }
    
    clear() {
        this.cache.clear();
    }
}

// Create global cache instance
window.apiCache = new APICache();

// 6. Minimize repaints - batch DOM updates
function batchDOMUpdates(updateFn) {
    requestAnimationFrame(updateFn);
}

// 7. Defer non-critical JavaScript
function deferScript(src) {
    const script = document.createElement('script');
    script.src = src;
    script.defer = true;
    document.head.appendChild(script);
}

// 8. Preload critical resources
function preloadResource(href, as = 'script') {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = as;
    link.href = href;
    document.head.appendChild(link);
}

// 9. Virtual scrolling for large lists
class VirtualList {
    constructor(container, items, itemHeight, renderItem) {
        this.container = container;
        this.items = items;
        this.itemHeight = itemHeight;
        this.renderItem = renderItem;
        this.visibleRange = { start: 0, end: 0 };
        
        this.container.addEventListener('scroll', throttle(() => this.updateVisibleRange(), 100));
        this.updateVisibleRange();
    }
    
    updateVisibleRange() {
        const scrollTop = this.container.scrollTop;
        const containerHeight = this.container.clientHeight;
        
        this.visibleRange.start = Math.floor(scrollTop / this.itemHeight);
        this.visibleRange.end = Math.ceil((scrollTop + containerHeight) / this.itemHeight);
        
        this.render();
    }
    
    render() {
        this.container.innerHTML = '';
        
        for (let i = this.visibleRange.start; i < Math.min(this.visibleRange.end, this.items.length); i++) {
            const item = this.items[i];
            const element = this.renderItem(item, i);
            element.style.transform = `translateY(${i * this.itemHeight}px)`;
            this.container.appendChild(element);
        }
    }
}

// 10. Web Worker for heavy computations
function runHeavyTask(task, data) {
    return new Promise((resolve, reject) => {
        const blob = new Blob([`
            self.onmessage = function(e) {
                const result = (${task})(e.data);
                self.postMessage(result);
            }
        `], { type: 'application/javascript' });
        
        const worker = new Worker(URL.createObjectURL(blob));
        worker.onmessage = (e) => {
            resolve(e.data);
            worker.terminate();
        };
        worker.onerror = reject;
        worker.postMessage(data);
    });
}

// Export for use
window.PerformanceUtils = {
    debounce,
    throttle,
    smoothScroll,
    APICache,
    batchDOMUpdates,
    deferScript,
    preloadResource,
    VirtualList,
    runHeavyTask
};
