/**
 * Utility functions for Audio Transcriber Application
 * Additional helper functions and validators
 */

// Extend AudioTranscriber namespace
AudioTranscriber.validators = {
    /**
     * Comprehensive file validation
     * @param {File} file - File to validate
     * @returns {object} Validation result with success flag and error message
     */
    validateFile: function(file) {
        const result = {
            success: true,
            errors: [],
            warnings: []
        };

        // Check if file exists
        if (!file) {
            result.success = false;
            result.errors.push('No file selected');
            return result;
        }

        // Validate file name
        if (!file.name || file.name.trim() === '') {
            result.success = false;
            result.errors.push('File name is required');
        }

        // Validate file extension
        if (!AudioTranscriber.utils.isValidFileFormat(file)) {
            result.success = false;
            result.errors.push(
                `Unsupported file format. Please use: ${AudioTranscriber.constants.SUPPORTED_FORMATS.join(', ').toUpperCase()}`
            );
        }

        // Validate file size
        if (!AudioTranscriber.utils.isValidFileSize(file)) {
            result.success = false;
            result.errors.push(
                `File size exceeds maximum limit of ${AudioTranscriber.utils.formatFileSize(AudioTranscriber.constants.MAX_FILE_SIZE)}`
            );
        }

        // Check for empty file
        if (file.size === 0) {
            result.success = false;
            result.errors.push('File appears to be empty');
        }

        // Warnings for large files
        if (file.size > 100 * 1024 * 1024) { // 100MB
            result.warnings.push('Large file detected - upload may take longer');
        }

        // Warning for unusual file names
        if (file.name.includes(' ')) {
            result.warnings.push('File name contains spaces - consider using underscores');
        }

        return result;
    },

    /**
     * Validate audio file headers (basic check)
     * @param {File} file - File to validate
     * @returns {Promise<object>} Validation result
     */
    validateAudioHeaders: async function(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            const chunkSize = 12; // Read first 12 bytes
            
            reader.onload = function(e) {
                const arrayBuffer = e.target.result;
                const uint8Array = new Uint8Array(arrayBuffer);
                const result = {
                    success: true,
                    format: 'unknown',
                    errors: []
                };

                try {
                    // Check WAV header
                    if (uint8Array.length >= 12) {
                        const riffHeader = String.fromCharCode(...uint8Array.slice(0, 4));
                        const waveHeader = String.fromCharCode(...uint8Array.slice(8, 12));
                        
                        if (riffHeader === 'RIFF' && waveHeader === 'WAVE') {
                            result.format = 'wav';
                            resolve(result);
                            return;
                        }
                    }

                    // Check MP3 header
                    if (uint8Array.length >= 3) {
                        // MP3 frame header starts with 0xFF and second byte starts with 0xF (11 bits)
                        if (uint8Array[0] === 0xFF && (uint8Array[1] & 0xE0) === 0xE0) {
                            result.format = 'mp3';
                            resolve(result);
                            return;
                        }

                        // Check for ID3 tag
                        const id3Header = String.fromCharCode(...uint8Array.slice(0, 3));
                        if (id3Header === 'ID3') {
                            result.format = 'mp3';
                            resolve(result);
                            return;
                        }
                    }

                    // Check FLAC header
                    if (uint8Array.length >= 4) {
                        const flacHeader = String.fromCharCode(...uint8Array.slice(0, 4));
                        if (flacHeader === 'fLaC') {
                            result.format = 'flac';
                            resolve(result);
                            return;
                        }
                    }

                    // If no known format detected but file extension suggests audio
                    const extension = AudioTranscriber.utils.getFileExtension(file.name);
                    if (AudioTranscriber.constants.SUPPORTED_FORMATS.includes(extension)) {
                        result.format = extension;
                        result.warnings = ['Could not verify file format from headers, trusting file extension'];
                    } else {
                        result.success = false;
                        result.errors.push('File does not appear to be a valid audio file');
                    }

                } catch (error) {
                    result.success = false;
                    result.errors.push('Error reading file headers');
                    console.error('Header validation error:', error);
                }

                resolve(result);
            };

            reader.onerror = function() {
                resolve({
                    success: false,
                    format: 'unknown',
                    errors: ['Error reading file']
                });
            };

            const blob = file.slice(0, chunkSize);
            reader.readAsArrayBuffer(blob);
        });
    }
};

// Audio analysis utilities
AudioTranscriber.audio = {
    /**
     * Get audio duration using HTML5 Audio API
     * @param {File} file - Audio file
     * @returns {Promise<number>} Duration in seconds
     */
    getDuration: function(file) {
        return new Promise((resolve, reject) => {
            const audio = new Audio();
            const url = URL.createObjectURL(file);
            
            audio.addEventListener('loadedmetadata', function() {
                URL.revokeObjectURL(url);
                resolve(audio.duration);
            });
            
            audio.addEventListener('error', function() {
                URL.revokeObjectURL(url);
                reject(new Error('Could not load audio file'));
            });
            
            audio.src = url;
        });
    },

    /**
     * Extract basic audio metadata
     * @param {File} file - Audio file
     * @returns {Promise<object>} Metadata object
     */
    extractMetadata: async function(file) {
        const metadata = {
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: new Date(file.lastModified),
            extension: AudioTranscriber.utils.getFileExtension(file.name),
            duration: null,
            format: null
        };

        try {
            // Get duration
            metadata.duration = await this.getDuration(file);
        } catch (error) {
            console.warn('Could not extract duration:', error);
            metadata.duration = null;
        }

        try {
            // Validate headers and get format
            const validation = await AudioTranscriber.validators.validateAudioHeaders(file);
            metadata.format = validation.format;
        } catch (error) {
            console.warn('Could not validate headers:', error);
            metadata.format = metadata.extension;
        }

        return metadata;
    }
};

// UI animation utilities
AudioTranscriber.animations = {
    /**
     * Animate progress bar
     * @param {Element} progressBar - Progress bar element
     * @param {number} targetPercent - Target percentage
     * @param {number} duration - Animation duration in ms
     */
    animateProgress: function(progressBar, targetPercent, duration = 300) {
        if (!progressBar) return;

        const startPercent = parseFloat(progressBar.style.width) || 0;
        const difference = targetPercent - startPercent;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (ease-out)
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const currentPercent = startPercent + (difference * easeOut);
            
            progressBar.style.width = `${currentPercent}%`;
            progressBar.setAttribute('aria-valuenow', currentPercent);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    },

    /**
     * Shake element animation
     * @param {Element} element - Element to shake
     */
    shake: function(element) {
        if (!element) return;

        element.classList.add('validation-shake');
        setTimeout(() => {
            element.classList.remove('validation-shake');
        }, 500);
    },

    /**
     * Pulse element animation
     * @param {Element} element - Element to pulse
     * @param {number} duration - Pulse duration in ms
     */
    pulse: function(element, duration = 1000) {
        if (!element) return;

        element.style.transition = `opacity ${duration / 2}ms ease-in-out`;
        element.style.opacity = '0.5';
        
        setTimeout(() => {
            element.style.opacity = '1';
            setTimeout(() => {
                element.style.transition = '';
            }, duration / 2);
        }, duration / 2);
    }
};

// Browser compatibility checks
AudioTranscriber.compatibility = {
    /**
     * Check if File API is supported
     * @returns {boolean} True if supported
     */
    hasFileAPI: function() {
        return !!(window.File && window.FileReader && window.FileList && window.Blob);
    },

    /**
     * Check if drag and drop is supported
     * @returns {boolean} True if supported
     */
    hasDragAndDrop: function() {
        const div = document.createElement('div');
        return ('draggable' in div) || ('ondragstart' in div && 'ondrop' in div);
    },

    /**
     * Check if XMLHttpRequest Level 2 is supported
     * @returns {boolean} True if supported
     */
    hasXHR2: function() {
        return !!(window.XMLHttpRequest && 'upload' in new XMLHttpRequest());
    },

    /**
     * Get browser compatibility status
     * @returns {object} Compatibility status
     */
    getStatus: function() {
        return {
            fileAPI: this.hasFileAPI(),
            dragAndDrop: this.hasDragAndDrop(),
            xhr2: this.hasXHR2(),
            supported: this.hasFileAPI() && this.hasXHR2()
        };
    },

    /**
     * Display compatibility warnings if needed
     */
    checkAndWarn: function() {
        const status = this.getStatus();
        
        if (!status.supported) {
            const message = 'Your browser does not fully support file uploads. Please use a modern browser like Chrome, Firefox, Safari, or Edge.';
            AudioTranscriber.utils.showToast(message, 'warning', 8000);
        } else if (!status.dragAndDrop) {
            const message = 'Drag and drop is not supported in your browser. You can still use the file selection button.';
            AudioTranscriber.utils.showToast(message, 'info', 5000);
        }
    }
};

// Initialize compatibility check when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    AudioTranscriber.compatibility.checkAndWarn();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioTranscriber;
}