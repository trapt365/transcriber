/**
 * Main JavaScript file for Audio Transcriber Application
 * Handles global functionality and utilities
 */

// Global application namespace
window.AudioTranscriber = window.AudioTranscriber || {};

// Application constants
AudioTranscriber.constants = {
    // File validation
    SUPPORTED_FORMATS: ['wav', 'mp3', 'flac'],
    SUPPORTED_MIME_TYPES: ['audio/wav', 'audio/mpeg', 'audio/flac', 'audio/x-flac'],
    MAX_FILE_SIZE: 500 * 1024 * 1024, // 500MB in bytes
    
    // API endpoints
    API_BASE: '/api/v1',
    UPLOAD_ENDPOINT: '/api/v1/upload',
    
    // UI constants
    PROGRESS_UPDATE_INTERVAL: 100, // milliseconds
    ERROR_DISPLAY_DURATION: 5000, // milliseconds
    SUCCESS_DISPLAY_DURATION: 3000, // milliseconds
};

// Global utility functions
AudioTranscriber.utils = {
    /**
     * Format file size in human readable format
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Format duration in minutes and seconds
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration
     */
    formatDuration: function(seconds) {
        if (!seconds || isNaN(seconds)) return 'Unknown';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        if (minutes === 0) {
            return `${remainingSeconds}s`;
        }
        
        return `${minutes}m ${remainingSeconds}s`;
    },

    /**
     * Format transfer speed
     * @param {number} bytesPerSecond - Transfer speed in bytes per second
     * @returns {string} Formatted speed
     */
    formatSpeed: function(bytesPerSecond) {
        if (!bytesPerSecond || bytesPerSecond === 0) return '';
        
        const mbps = bytesPerSecond / (1024 * 1024);
        if (mbps < 0.1) {
            const kbps = bytesPerSecond / 1024;
            return `${kbps.toFixed(1)} KB/s`;
        }
        
        return `${mbps.toFixed(1)} MB/s`;
    },

    /**
     * Get file extension from filename
     * @param {string} filename - File name
     * @returns {string} File extension in lowercase
     */
    getFileExtension: function(filename) {
        return filename.split('.').pop().toLowerCase();
    },

    /**
     * Validate file format
     * @param {File} file - File object
     * @returns {boolean} True if file format is supported
     */
    isValidFileFormat: function(file) {
        const extension = this.getFileExtension(file.name);
        const mimeType = file.type;
        
        return AudioTranscriber.constants.SUPPORTED_FORMATS.includes(extension) ||
               AudioTranscriber.constants.SUPPORTED_MIME_TYPES.includes(mimeType);
    },

    /**
     * Validate file size
     * @param {File} file - File object
     * @returns {boolean} True if file size is within limits
     */
    isValidFileSize: function(file) {
        return file.size <= AudioTranscriber.constants.MAX_FILE_SIZE;
    },

    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type of toast (success, error, warning, info)
     * @param {number} duration - Display duration in milliseconds
     */
    showToast: function(message, type = 'info', duration = 3000) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.remove('show');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 150);
            }
        }, duration);
    },

    /**
     * Debounce function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Get CSRF token from meta tag or form
     * @returns {string} CSRF token
     */
    getCSRFToken: function() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) {
            return inputToken.value;
        }
        
        return '';
    },

    /**
     * Make HTTP request with error handling
     * @param {string} url - Request URL
     * @param {object} options - Request options
     * @returns {Promise} Request promise
     */
    request: async function(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        const config = { ...defaultOptions, ...options };
        
        // Add CSRF token for non-GET requests
        if (config.method !== 'GET') {
            const csrfToken = this.getCSRFToken();
            if (csrfToken) {
                config.headers['X-CSRFToken'] = csrfToken;
            }
        }
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            throw error;
        }
    }
};

// DOM utility functions
AudioTranscriber.dom = {
    /**
     * Get element by ID with error handling
     * @param {string} id - Element ID
     * @returns {Element|null} DOM element
     */
    getElementById: function(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with ID '${id}' not found`);
        }
        return element;
    },

    /**
     * Show element with animation
     * @param {Element} element - Element to show
     * @param {string} display - Display type (default: block)
     */
    show: function(element, display = 'block') {
        if (element) {
            element.style.display = display;
            element.classList.remove('d-none');
            element.classList.add('fade-in');
        }
    },

    /**
     * Hide element with animation
     * @param {Element} element - Element to hide
     */
    hide: function(element) {
        if (element) {
            element.classList.add('d-none');
            element.classList.remove('fade-in');
        }
    },

    /**
     * Toggle element visibility
     * @param {Element} element - Element to toggle
     * @param {string} display - Display type when showing
     */
    toggle: function(element, display = 'block') {
        if (element) {
            if (element.classList.contains('d-none')) {
                this.show(element, display);
            } else {
                this.hide(element);
            }
        }
    }
};

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Audio Transcriber application initialized');
    
    // Global error handler
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        AudioTranscriber.utils.showToast(
            'An unexpected error occurred. Please refresh the page and try again.',
            'error',
            5000
        );
    });
    
    // Global unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        AudioTranscriber.utils.showToast(
            'A network error occurred. Please check your connection and try again.',
            'error',
            5000
        );
    });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioTranscriber;
}