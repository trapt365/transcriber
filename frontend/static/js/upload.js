/**
 * Upload functionality for Audio Transcriber Application
 * Handles file upload, drag-and-drop, progress tracking, and validation
 */

// Upload module
AudioTranscriber.upload = {
    // Upload state
    state: {
        currentFile: null,
        isUploading: false,
        uploadXHR: null,
        startTime: null,
        lastProgress: 0,
        speedSamples: []
    },

    // DOM elements cache
    elements: {},

    /**
     * Initialize upload functionality
     */
    init: function() {
        console.log('Initializing upload functionality');
        
        // Cache DOM elements
        this.cacheElements();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Check browser compatibility
        this.checkCompatibility();
    },

    /**
     * Cache frequently used DOM elements
     */
    cacheElements: function() {
        this.elements = {
            uploadForm: AudioTranscriber.dom.getElementById('uploadForm'),
            dropZone: AudioTranscriber.dom.getElementById('dropZone'),
            dropZoneContent: AudioTranscriber.dom.getElementById('dropZoneContent'),
            audioFile: AudioTranscriber.dom.getElementById('audioFile'),
            browseBtn: AudioTranscriber.dom.getElementById('browseBtn'),
            uploadProgress: AudioTranscriber.dom.getElementById('uploadProgress'),
            progressBar: AudioTranscriber.dom.getElementById('progressBar'),
            progressText: AudioTranscriber.dom.getElementById('progressText'),
            speedText: AudioTranscriber.dom.getElementById('speedText'),
            timeRemaining: AudioTranscriber.dom.getElementById('timeRemaining'),
            fileName: AudioTranscriber.dom.getElementById('fileName'),
            cancelBtn: AudioTranscriber.dom.getElementById('cancelBtn'),
            fileInfo: AudioTranscriber.dom.getElementById('fileInfo'),
            fileSize: AudioTranscriber.dom.getElementById('fileSize'),
            fileDuration: AudioTranscriber.dom.getElementById('fileDuration'),
            fileFormat: AudioTranscriber.dom.getElementById('fileFormat'),
            errorDisplay: AudioTranscriber.dom.getElementById('errorDisplay'),
            errorMessage: AudioTranscriber.dom.getElementById('errorMessage'),
            successDisplay: AudioTranscriber.dom.getElementById('successDisplay'),
            successMessage: AudioTranscriber.dom.getElementById('successMessage'),
            submitBtn: AudioTranscriber.dom.getElementById('submitBtn')
        };
    },

    /**
     * Setup all event listeners
     */
    setupEventListeners: function() {
        // File input change
        if (this.elements.audioFile) {
            this.elements.audioFile.addEventListener('change', (e) => {
                this.handleFileSelect(e.target.files[0]);
            });
        }

        // Browse button click
        if (this.elements.browseBtn) {
            this.elements.browseBtn.addEventListener('click', () => {
                this.elements.audioFile?.click();
            });
        }

        // Form submission
        if (this.elements.uploadForm) {
            this.elements.uploadForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.startUpload();
            });
        }

        // Cancel upload
        if (this.elements.cancelBtn) {
            this.elements.cancelBtn.addEventListener('click', () => {
                this.cancelUpload();
            });
        }

        // Drag and drop events
        this.setupDragAndDrop();
    },

    /**
     * Setup drag and drop functionality
     */
    setupDragAndDrop: function() {
        if (!this.elements.dropZone) return;

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.elements.dropZone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            this.elements.dropZone.addEventListener(eventName, () => {
                this.elements.dropZone.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.elements.dropZone.addEventListener(eventName, () => {
                this.elements.dropZone.classList.remove('drag-over');
            }, false);
        });

        // Handle dropped files
        this.elements.dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        }, false);
    },

    /**
     * Prevent default drag behaviors
     */
    preventDefaults: function(e) {
        e.preventDefault();
        e.stopPropagation();
    },

    /**
     * Check browser compatibility
     */
    checkCompatibility: function() {
        const status = AudioTranscriber.compatibility.getStatus();
        
        if (!status.supported) {
            this.showError('Your browser does not support file uploads. Please use a modern browser.');
            this.disableUpload();
        }
    },

    /**
     * Handle file selection
     * @param {File} file - Selected file
     */
    handleFileSelect: async function(file) {
        if (!file) return;

        console.log('File selected:', file.name, file.size, file.type);

        // Reset previous state
        this.resetState();

        // Validate file
        const validation = AudioTranscriber.validators.validateFile(file);
        
        if (!validation.success) {
            this.showError(validation.errors.join(', '));
            AudioTranscriber.animations.shake(this.elements.dropZone);
            return;
        }

        // Show warnings if any
        if (validation.warnings.length > 0) {
            validation.warnings.forEach(warning => {
                AudioTranscriber.utils.showToast(warning, 'warning', 4000);
            });
        }

        // Store file
        this.state.currentFile = file;

        // Extract metadata
        try {
            const metadata = await AudioTranscriber.audio.extractMetadata(file);
            this.displayFileInfo(metadata);
            this.showSubmitButton();
        } catch (error) {
            console.error('Error extracting metadata:', error);
            // Still allow upload even if metadata extraction fails
            this.displayBasicFileInfo(file);
            this.showSubmitButton();
        }

        // Update UI
        this.hideError();
        this.hideSuccess();
    },

    /**
     * Display file information
     * @param {object} metadata - File metadata
     */
    displayFileInfo: function(metadata) {
        if (this.elements.fileSize) {
            this.elements.fileSize.textContent = AudioTranscriber.utils.formatFileSize(metadata.size);
        }

        if (this.elements.fileDuration) {
            this.elements.fileDuration.textContent = metadata.duration 
                ? AudioTranscriber.utils.formatDuration(metadata.duration)
                : 'Unknown';
        }

        if (this.elements.fileFormat) {
            this.elements.fileFormat.textContent = (metadata.format || metadata.extension).toUpperCase();
        }

        AudioTranscriber.dom.show(this.elements.fileInfo);
    },

    /**
     * Display basic file information when metadata extraction fails
     * @param {File} file - File object
     */
    displayBasicFileInfo: function(file) {
        if (this.elements.fileSize) {
            this.elements.fileSize.textContent = AudioTranscriber.utils.formatFileSize(file.size);
        }

        if (this.elements.fileDuration) {
            this.elements.fileDuration.textContent = 'Calculating...';
        }

        if (this.elements.fileFormat) {
            this.elements.fileFormat.textContent = AudioTranscriber.utils.getFileExtension(file.name).toUpperCase();
        }

        AudioTranscriber.dom.show(this.elements.fileInfo);
    },

    /**
     * Show submit button
     */
    showSubmitButton: function() {
        AudioTranscriber.dom.show(this.elements.submitBtn, 'inline-block');
    },

    /**
     * Hide submit button
     */
    hideSubmitButton: function() {
        AudioTranscriber.dom.hide(this.elements.submitBtn);
    },

    /**
     * Start upload process
     */
    startUpload: function() {
        if (!this.state.currentFile || this.state.isUploading) {
            return;
        }

        console.log('Starting upload for:', this.state.currentFile.name);

        // Update UI
        this.state.isUploading = true;
        this.state.startTime = Date.now();
        this.state.speedSamples = [];
        
        this.showProgress();
        this.hideError();
        this.hideSuccess();
        this.hideSubmitButton();

        // Update drop zone style
        this.elements.dropZone?.classList.add('uploading');

        // Create form data
        const formData = new FormData();
        formData.append('file', this.state.currentFile);

        // Add CSRF token
        const csrfToken = AudioTranscriber.utils.getCSRFToken();
        if (csrfToken) {
            formData.append('csrf_token', csrfToken);
        }

        // Create XMLHttpRequest
        this.state.uploadXHR = new XMLHttpRequest();

        // Setup progress tracking
        this.state.uploadXHR.upload.addEventListener('progress', (e) => {
            this.updateProgress(e);
        });

        // Setup completion handlers
        this.state.uploadXHR.addEventListener('load', () => {
            this.handleUploadComplete();
        });

        this.state.uploadXHR.addEventListener('error', () => {
            this.handleUploadError('Network error occurred during upload');
        });

        this.state.uploadXHR.addEventListener('abort', () => {
            this.handleUploadCancel();
        });

        this.state.uploadXHR.addEventListener('timeout', () => {
            this.handleUploadError('Upload timed out');
        });

        // Configure request
        this.state.uploadXHR.open('POST', AudioTranscriber.constants.UPLOAD_ENDPOINT);
        this.state.uploadXHR.timeout = 300000; // 5 minutes timeout

        // Start upload
        this.state.uploadXHR.send(formData);

        // Update file name in progress display
        if (this.elements.fileName) {
            this.elements.fileName.textContent = this.state.currentFile.name;
        }
    },

    /**
     * Update upload progress
     * @param {ProgressEvent} event - Progress event
     */
    updateProgress: function(event) {
        if (!event.lengthComputable) return;

        const percent = Math.round((event.loaded / event.total) * 100);
        const currentTime = Date.now();
        const elapsedTime = (currentTime - this.state.startTime) / 1000; // seconds

        // Update progress bar
        if (this.elements.progressBar) {
            AudioTranscriber.animations.animateProgress(this.elements.progressBar, percent);
        }

        // Update progress text
        if (this.elements.progressText) {
            this.elements.progressText.textContent = `${percent}%`;
        }

        // Calculate and display speed
        if (elapsedTime > 0) {
            const speed = event.loaded / elapsedTime; // bytes per second
            
            // Store speed sample for smoothing
            this.state.speedSamples.push(speed);
            if (this.state.speedSamples.length > 10) {
                this.state.speedSamples.shift();
            }

            // Calculate average speed
            const avgSpeed = this.state.speedSamples.reduce((a, b) => a + b, 0) / this.state.speedSamples.length;
            
            if (this.elements.speedText) {
                this.elements.speedText.textContent = AudioTranscriber.utils.formatSpeed(avgSpeed);
            }

            // Calculate and display estimated time remaining
            if (avgSpeed > 0 && percent < 100) {
                const remainingBytes = event.total - event.loaded;
                const remainingTime = remainingBytes / avgSpeed;
                
                if (this.elements.timeRemaining && remainingTime < 3600) { // Only show if less than 1 hour
                    this.elements.timeRemaining.textContent = `~${Math.ceil(remainingTime)}s remaining`;
                }
            }
        }

        this.state.lastProgress = percent;
    },

    /**
     * Handle upload completion
     */
    handleUploadComplete: function() {
        console.log('Upload completed');

        if (this.state.uploadXHR.status === 200) {
            try {
                const response = JSON.parse(this.state.uploadXHR.responseText);
                
                if (response.success) {
                    this.handleUploadSuccess(response);
                } else {
                    this.handleUploadError(response.message || 'Upload failed');
                }
            } catch (error) {
                console.error('Error parsing response:', error);
                this.handleUploadError('Invalid response from server');
            }
        } else {
            this.handleUploadError(`Server error: ${this.state.uploadXHR.status}`);
        }
    },

    /**
     * Handle successful upload
     * @param {object} response - Server response
     */
    handleUploadSuccess: function(response) {
        console.log('Upload successful:', response);

        // Update UI
        this.elements.dropZone?.classList.remove('uploading');
        this.elements.dropZone?.classList.add('upload-complete');

        // Complete progress bar
        if (this.elements.progressBar) {
            AudioTranscriber.animations.animateProgress(this.elements.progressBar, 100);
        }

        if (this.elements.progressText) {
            this.elements.progressText.textContent = '100%';
        }

        // Show success message
        this.showSuccess(response.message || 'File uploaded successfully!');

        // Reset state
        this.state.isUploading = false;
        this.state.uploadXHR = null;

        // Redirect to status page or update UI
        if (response.job_id) {
            setTimeout(() => {
                this.redirectToStatus(response.job_id);
            }, 2000);
        }
    },

    /**
     * Handle upload error
     * @param {string} message - Error message
     */
    handleUploadError: function(message) {
        console.error('Upload error:', message);

        // Update UI
        this.elements.dropZone?.classList.remove('uploading');
        this.elements.dropZone?.classList.add('upload-error');

        this.hideProgress();
        this.showError(message);
        this.showSubmitButton();

        // Reset state
        this.state.isUploading = false;
        this.state.uploadXHR = null;

        // Shake animation
        AudioTranscriber.animations.shake(this.elements.dropZone);
    },

    /**
     * Handle upload cancellation
     */
    handleUploadCancel: function() {
        console.log('Upload cancelled');

        // Update UI
        this.elements.dropZone?.classList.remove('uploading');
        this.hideProgress();
        this.showSubmitButton();

        // Show info message
        AudioTranscriber.utils.showToast('Upload cancelled', 'info', 3000);

        // Reset state
        this.state.isUploading = false;
        this.state.uploadXHR = null;
    },

    /**
     * Cancel ongoing upload
     */
    cancelUpload: function() {
        if (this.state.uploadXHR && this.state.isUploading) {
            this.state.uploadXHR.abort();
        }
    },

    /**
     * Show upload progress
     */
    showProgress: function() {
        AudioTranscriber.dom.hide(this.elements.dropZoneContent);
        AudioTranscriber.dom.show(this.elements.uploadProgress);
    },

    /**
     * Hide upload progress
     */
    hideProgress: function() {
        AudioTranscriber.dom.show(this.elements.dropZoneContent);
        AudioTranscriber.dom.hide(this.elements.uploadProgress);
    },

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError: function(message) {
        if (this.elements.errorMessage) {
            this.elements.errorMessage.textContent = message;
        }
        AudioTranscriber.dom.show(this.elements.errorDisplay);
        this.hideSuccess();
    },

    /**
     * Hide error message
     */
    hideError: function() {
        AudioTranscriber.dom.hide(this.elements.errorDisplay);
    },

    /**
     * Show success message
     * @param {string} message - Success message
     */
    showSuccess: function(message) {
        if (this.elements.successMessage) {
            this.elements.successMessage.textContent = message;
        }
        AudioTranscriber.dom.show(this.elements.successDisplay);
        this.hideError();
    },

    /**
     * Hide success message
     */
    hideSuccess: function() {
        AudioTranscriber.dom.hide(this.elements.successDisplay);
    },

    /**
     * Reset upload state
     */
    resetState: function() {
        this.state.currentFile = null;
        this.state.isUploading = false;
        this.state.uploadXHR = null;
        this.state.startTime = null;
        this.state.lastProgress = 0;
        this.state.speedSamples = [];

        // Reset UI
        this.elements.dropZone?.classList.remove('uploading', 'upload-complete', 'upload-error');
        this.hideProgress();
        this.hideError();
        this.hideSuccess();
        this.hideSubmitButton();
        AudioTranscriber.dom.hide(this.elements.fileInfo);

        // Reset progress
        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = '0%';
        }
    },

    /**
     * Disable upload functionality
     */
    disableUpload: function() {
        if (this.elements.uploadForm) {
            this.elements.uploadForm.classList.add('disabled');
        }
        
        if (this.elements.browseBtn) {
            this.elements.browseBtn.disabled = true;
        }
        
        if (this.elements.dropZone) {
            this.elements.dropZone.style.pointerEvents = 'none';
            this.elements.dropZone.style.opacity = '0.5';
        }
    },

    /**
     * Redirect to status page
     * @param {string} jobId - Job ID
     */
    redirectToStatus: function(jobId) {
        const statusUrl = `/status/${jobId}`;
        console.log('Redirecting to:', statusUrl);
        window.location.href = statusUrl;
    }
};

// Initialize upload functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the upload page
    if (document.getElementById('uploadForm')) {
        AudioTranscriber.upload.init();
    }
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioTranscriber.upload;
}