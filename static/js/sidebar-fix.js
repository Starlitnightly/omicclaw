/**
 * Sidebar Fix - Disable automatic minimenu on resize
 * This script removes the automatic sidebar collapse behavior on window resize
 */

(function() {
    // Remove minimenu class on load and prevent it from being added
    document.addEventListener('DOMContentLoaded', function() {
        const html = document.documentElement;

        // Remove minimenu class
        html.classList.remove('minimenu');

        // Override the resize handler by removing all resize event listeners
        // and adding our own that does nothing related to minimenu
        const oldResize = window.onresize;

        // Create a MutationObserver to watch for minimenu class changes
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    if (html.classList.contains('minimenu')) {
                        // Remove minimenu class if it gets added
                        html.classList.remove('minimenu');
                    }
                }
            });
        });

        // Start observing
        observer.observe(html, {
            attributes: true,
            attributeFilter: ['class']
        });

        console.log('Sidebar auto-collapse disabled');
    });
})();
