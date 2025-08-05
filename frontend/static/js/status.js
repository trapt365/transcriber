/**
 * Status page functionality for Audio Transcriber Application
 * Handles job status polling, results display, and user interactions
 */

// Status module
AudioTranscriber.status = {
    // State management
    state: {
        jobId: null,
        currentStatus: null,
        pollInterval: null,
        isPolling: false,
        lastUpdate: null,
        refreshCount: 0
    },

    // Configuration
    config: {
        pollIntervalMs: 3000, // 3 seconds
        maxPollAttempts: 200, // ~10 minutes max polling
        refreshTimeout: 30000 // 30 seconds timeout for requests
    },

    // DOM elements cache
    elements: {},

    /**
     * Initialize status page functionality
     * @param {object} options - Initialization options
     */
    init: function(options = {}) {
        console.log('Initializing status page functionality');
        
        // Set initial state
        this.state.jobId = options.jobId;
        this.state.currentStatus = options.initialStatus;
        
        // Cache DOM elements
        this.cacheElements();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start initial status check
        this.updateStatus();
        
        // Start polling if job is not completed
        if (this.shouldPoll(this.state.currentStatus)) {
            this.startPolling();
        }
    },

    /**
     * Cache frequently used DOM elements
     */
    cacheElements: function() {
        this.elements = {
            statusBadge: AudioTranscriber.dom.getElementById('statusBadge'),
            progressBar: AudioTranscriber.dom.getElementById('progressBar'),
            jobId: AudioTranscriber.dom.getElementById('jobId'),
            fileName: AudioTranscriber.dom.getElementById('fileName'),
            createdAt: AudioTranscriber.dom.getElementById('createdAt'),
            fileSize: AudioTranscriber.dom.getElementById('fileSize'),
            
            errorSection: AudioTranscriber.dom.getElementById('errorSection'),
            errorMessage: AudioTranscriber.dom.getElementById('errorMessage'),
            
            processingSection: AudioTranscriber.dom.getElementById('processingSection'),
            
            resultsSection: AudioTranscriber.dom.getElementById('resultsSection'),
            confidenceScore: AudioTranscriber.dom.getElementById('confidenceScore'),
            wordCount: AudioTranscriber.dom.getElementById('wordCount'),
            speakerCount: AudioTranscriber.dom.getElementById('speakerCount'),
            processingTime: AudioTranscriber.dom.getElementById('processingTime'),
            transcriptText: AudioTranscriber.dom.getElementById('transcriptText'),
            speakersSection: AudioTranscriber.dom.getElementById('speakersSection'),
            speakersList: AudioTranscriber.dom.getElementById('speakersList'),
            segmentsList: AudioTranscriber.dom.getElementById('segmentsList'),
            
            refreshBtn: AudioTranscriber.dom.getElementById('refreshBtn'),
            cancelBtn: AudioTranscriber.dom.getElementById('cancelBtn'),
            newUploadBtn: AudioTranscriber.dom.getElementById('newUploadBtn'),
            copyBtn: AudioTranscriber.dom.getElementById('copyBtn'),
            downloadBtn: AudioTranscriber.dom.getElementById('downloadBtn'),
            toggleSegments: AudioTranscriber.dom.getElementById('toggleSegments')
        };
    },

    /**
     * Setup event listeners
     */
    setupEventListeners: function() {
        // Refresh button
        if (this.elements.refreshBtn) {
            this.elements.refreshBtn.addEventListener('click', () => {
                this.handleRefresh();
            });
        }

        // Cancel button
        if (this.elements.cancelBtn) {
            this.elements.cancelBtn.addEventListener('click', () => {
                this.handleCancel();
            });
        }

        // Copy button
        if (this.elements.copyBtn) {
            this.elements.copyBtn.addEventListener('click', () => {
                this.copyTranscript();
            });
        }

        // Download button
        if (this.elements.downloadBtn) {
            this.elements.downloadBtn.addEventListener('click', () => {
                this.downloadTranscript();
            });
        }

        // Toggle segments
        if (this.elements.toggleSegments) {
            this.elements.toggleSegments.addEventListener('click', () => {
                this.toggleSegments();
            });
        }

        // Auto-refresh when page becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.shouldPoll(this.state.currentStatus)) {
                this.updateStatus();
                if (!this.state.isPolling) {
                    this.startPolling();
                }
            }
        });
    },

    /**
     * Check if status should be polled
     * @param {string} status - Current job status
     * @returns {boolean} True if should poll
     */
    shouldPoll: function(status) {
        return status && !['completed', 'failed'].includes(status.toLowerCase());
    },

    /**
     * Start status polling
     */
    startPolling: function() {
        if (this.state.isPolling) return;
        
        console.log('Starting status polling');
        this.state.isPolling = true;
        this.state.refreshCount = 0;
        
        this.state.pollInterval = setInterval(() => {
            this.state.refreshCount++;
            
            if (this.state.refreshCount > this.config.maxPollAttempts) {
                console.log('Max poll attempts reached, stopping polling');
                this.stopPolling();
                this.showAutoRefreshStopped();
                return;
            }
            
            this.updateStatus();
        }, this.config.pollIntervalMs);
    },

    /**
     * Stop status polling
     */
    stopPolling: function() {
        if (this.state.pollInterval) {
            clearInterval(this.state.pollInterval);
            this.state.pollInterval = null;
        }
        this.state.isPolling = false;
        console.log('Status polling stopped');
    },

    /**
     * Update job status
     */
    updateStatus: async function() {
        if (!this.state.jobId) return;
        
        try {
            console.log(`Updating status for job: ${this.state.jobId}`);
            
            const response = await fetch(`/api/v1/jobs/${this.state.jobId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: this.config.refreshTimeout
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.message || 'Failed to get job status');
            }
            
            this.handleStatusUpdate(data.job, data.result);
            
        } catch (error) {
            console.error('Error updating status:', error);
            this.handleStatusError(error.message);
        }
    },

    /**
     * Handle status update response
     * @param {object} job - Job data
     * @param {object} result - Result data (if available)
     */
    handleStatusUpdate: function(job, result) {
        const oldStatus = this.state.currentStatus;
        this.state.currentStatus = job.status;
        this.state.lastUpdate = new Date();
        
        console.log(`Status updated: ${oldStatus} -> ${job.status}`);
        
        // Update UI based on status
        this.updateStatusDisplay(job);
        
        // Handle status-specific updates
        switch (job.status.toLowerCase()) {
            case 'uploaded':
                this.showUploadedState(job);
                break;
            case 'processing':
                this.showProcessingState(job);
                break;
            case 'completed':
                this.showCompletedState(job, result);
                this.stopPolling();
                break;
            case 'failed':
                this.showFailedState(job);
                this.stopPolling();
                break;
        }
        
        // Show auto-refresh indicator if polling
        if (this.state.isPolling) {
            this.showAutoRefreshIndicator();
        }
    },

    /**
     * Update status display elements
     * @param {object} job - Job data
     */
    updateStatusDisplay: function(job) {
        // Update status badge
        if (this.elements.statusBadge) {
            this.elements.statusBadge.textContent = job.status.charAt(0).toUpperCase() + job.status.slice(1);
            this.elements.statusBadge.className = `badge status-${job.status.toLowerCase()}`;
        }
        
        // Update progress bar
        if (this.elements.progressBar) {
            const progress = job.progress || 0;
            AudioTranscriber.animations.animateProgress(this.elements.progressBar, progress);
            
            // Update progress bar color based on status
            this.elements.progressBar.className = 'progress-bar progress-bar-striped';
            if (job.status.toLowerCase() === 'completed') {
                this.elements.progressBar.classList.add('bg-success');
            } else if (job.status.toLowerCase() === 'failed') {
                this.elements.progressBar.classList.add('bg-danger');
            } else if (job.status.toLowerCase() === 'processing') {
                this.elements.progressBar.classList.add('bg-warning', 'progress-bar-animated');
            }
        }
    },

    /**
     * Show uploaded state
     * @param {object} job - Job data
     */
    showUploadedState: function(job) {
        this.hideAllSections();
        
        // Show cancel button
        AudioTranscriber.dom.show(this.elements.cancelBtn);
    },

    /**
     * Show processing state
     * @param {object} job - Job data
     */
    showProcessingState: function(job) {
        this.hideAllSections();
        AudioTranscriber.dom.show(this.elements.processingSection);
        
        // Show cancel button
        AudioTranscriber.dom.show(this.elements.cancelBtn);
    },

    /**
     * Show completed state
     * @param {object} job - Job data
     * @param {object} result - Result data
     */
    showCompletedState: function(job, result) {
        this.hideAllSections();
        AudioTranscriber.dom.show(this.elements.resultsSection);
        AudioTranscriber.dom.show(this.elements.newUploadBtn);
        
        if (result) {
            this.displayResults(result);
        } else {
            // Fetch detailed results
            this.fetchResults();
        }
        
        // Hide cancel button
        AudioTranscriber.dom.hide(this.elements.cancelBtn);
    },

    /**
     * Show failed state
     * @param {object} job - Job data
     */
    showFailedState: function(job) {
        this.hideAllSections();
        AudioTranscriber.dom.show(this.elements.errorSection);
        AudioTranscriber.dom.show(this.elements.newUploadBtn);
        
        if (this.elements.errorMessage) {
            this.elements.errorMessage.textContent = job.error_message || 'Processing failed for unknown reason';
        }
        
        // Hide cancel button
        AudioTranscriber.dom.hide(this.elements.cancelBtn);
    },

    /**
     * Hide all status sections
     */
    hideAllSections: function() {
        AudioTranscriber.dom.hide(this.elements.errorSection);
        AudioTranscriber.dom.hide(this.elements.processingSection);
        AudioTranscriber.dom.hide(this.elements.resultsSection);
        AudioTranscriber.dom.hide(this.elements.cancelBtn);
        AudioTranscriber.dom.hide(this.elements.newUploadBtn);
    },

    /**
     * Fetch detailed results
     */
    fetchResults: async function() {
        try {
            const response = await fetch(`/api/v1/jobs/${this.state.jobId}/result`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.result) {
                this.displayResults(data.result);
            } else {
                throw new Error(data.message || 'Failed to fetch results');
            }
            
        } catch (error) {
            console.error('Error fetching results:', error);
            this.showResultsError(error.message);
        }
    },

    /**
     * Display transcription results
     * @param {object} result - Result data
     */
    displayResults: function(result) {
        console.log('Displaying results:', result);
        
        // Update statistics
        if (this.elements.confidenceScore) {
            this.elements.confidenceScore.textContent = result.confidence_score 
                ? `${Math.round(result.confidence_score * 100)}%` 
                : 'N/A';
        }
        
        if (this.elements.wordCount) {
            this.elements.wordCount.textContent = result.word_count || '0';
        }
        
        if (this.elements.speakerCount) {
            const speakerCount = result.speakers ? result.speakers.length : 0;
            this.elements.speakerCount.textContent = speakerCount;
        }
        
        if (this.elements.processingTime) {
            this.elements.processingTime.textContent = result.processing_duration 
                ? AudioTranscriber.utils.formatDuration(result.processing_duration)
                : 'N/A';
        }
        
        // Display transcript
        if (this.elements.transcriptText) {
            this.elements.transcriptText.textContent = result.transcript || 'No transcript available';
            this.elements.transcriptText.classList.remove('loading');
        }
        
        // Display speakers if available
        if (result.speakers && result.speakers.length > 0) {
            this.displaySpeakers(result.speakers);
            AudioTranscriber.dom.show(this.elements.speakersSection);
        }
        
        // Display segments
        if (result.segments && result.segments.length > 0) {
            this.displaySegments(result.segments);
        }
    },

    /**
     * Display speakers information
     * @param {Array} speakers - Speakers data
     */
    displaySpeakers: function(speakers) {
        if (!this.elements.speakersList) return;
        
        let html = '';
        
        speakers.forEach(speaker => {
            const confidence = speaker.confidence ? Math.round(speaker.confidence * 100) : 'N/A';
            const speakingTime = speaker.total_speaking_time 
                ? AudioTranscriber.utils.formatDuration(speaker.total_speaking_time)
                : 'Unknown';
            
            html += `
                <div class="speaker-card">
                    <div class="speaker-name">${speaker.name || `Speaker ${speaker.speaker_id}`}</div>
                    <div class="speaker-stats">
                        Speaking time: ${speakingTime} • 
                        Confidence: <span class="speaker-confidence">${confidence}%</span>
                    </div>
                </div>
            `;
        });
        
        this.elements.speakersList.innerHTML = html;
    },

    /**
     * Display transcript segments
     * @param {Array} segments - Segments data
     */
    displaySegments: function(segments) {
        if (!this.elements.segmentsList) return;
        
        let html = '';
        
        segments.forEach((segment, index) => {
            const startTime = this.formatTime(segment.start_time);
            const endTime = this.formatTime(segment.end_time);
            const confidence = segment.confidence ? Math.round(segment.confidence * 100) : 'N/A';
            const speakerName = segment.speaker_id ? `Speaker ${segment.speaker_id}` : 'Unknown';
            
            html += `
                <div class="segment-item">
                    <div class="d-flex align-items-center">
                        <span class="segment-timestamp">${startTime} - ${endTime}</span>
                        <span class="segment-speaker">${speakerName}</span>
                    </div>
                    <div class="segment-text">${segment.text || 'No text'}</div>
                    <div class="segment-confidence">Confidence: ${confidence}%</div>
                </div>
            `;
        });
        
        this.elements.segmentsList.innerHTML = html;
    },

    /**
     * Format time in seconds to MM:SS format
     * @param {number} seconds - Time in seconds
     * @returns {string} Formatted time
     */
    formatTime: function(seconds) {
        if (!seconds && seconds !== 0) return '00:00';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    /**
     * Handle manual refresh
     */
    handleRefresh: function() {
        console.log('Manual refresh triggered');
        
        // Add loading state to button
        const btn = this.elements.refreshBtn;
        if (btn) {
            btn.classList.add('refreshing');
            btn.disabled = true;
        }
        
        // Update status
        this.updateStatus().finally(() => {
            // Remove loading state
            if (btn) {
                btn.classList.remove('refreshing');
                btn.disabled = false;
            }
        });
    },

    /**
     * Handle job cancellation
     */
    handleCancel: async function() {
        if (!confirm('Are you sure you want to cancel this job?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/jobs/${this.state.jobId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': AudioTranscriber.utils.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                AudioTranscriber.utils.showToast('Job cancelled successfully', 'info', 3000);
                this.updateStatus(); // Refresh status
            } else {
                throw new Error(data.message || 'Failed to cancel job');
            }
            
        } catch (error) {
            console.error('Error cancelling job:', error);
            AudioTranscriber.utils.showToast('Failed to cancel job: ' + error.message, 'error', 5000);
        }
    },

    /**
     * Copy transcript to clipboard
     */
    copyTranscript: async function() {
        const transcript = this.elements.transcriptText?.textContent;
        
        if (!transcript) {
            AudioTranscriber.utils.showToast('No transcript available to copy', 'warning', 3000);
            return;
        }
        
        try {
            await navigator.clipboard.writeText(transcript);
            AudioTranscriber.utils.showToast('Transcript copied to clipboard', 'success', 2000);
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = transcript;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            AudioTranscriber.utils.showToast('Transcript copied to clipboard', 'success', 2000);
        }
    },

    /**
     * Download transcript as text file
     */
    downloadTranscript: function() {
        const transcript = this.elements.transcriptText?.textContent;
        const filename = this.elements.fileName?.textContent || 'transcript';
        
        if (!transcript) {
            AudioTranscriber.utils.showToast('No transcript available to download', 'warning', 3000);
            return;
        }
        
        const blob = new Blob([transcript], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename.replace(/\.[^/.]+$/, '')}_transcript.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
        
        AudioTranscriber.utils.showToast('Transcript downloaded', 'success', 2000);
    },

    /**
     * Toggle segments visibility
     */
    toggleSegments: function() {
        const segmentsList = this.elements.segmentsList;
        const toggleBtn = this.elements.toggleSegments;
        
        if (!segmentsList || !toggleBtn) return;
        
        const isVisible = !segmentsList.classList.contains('d-none');
        
        if (isVisible) {
            AudioTranscriber.dom.hide(segmentsList);
            toggleBtn.innerHTML = '<i class="bi bi-chevron-down"></i> Show Details';
            toggleBtn.classList.remove('expanded');
        } else {
            AudioTranscriber.dom.show(segmentsList);
            toggleBtn.innerHTML = '<i class="bi bi-chevron-up"></i> Hide Details';
            toggleBtn.classList.add('expanded');
        }
    },

    /**
     * Handle status error
     * @param {string} message - Error message
     */
    handleStatusError: function(message) {
        console.error('Status error:', message);
        
        // Show error toast but don't stop polling completely
        AudioTranscriber.utils.showToast('Error updating status: ' + message, 'error', 5000);
        
        // If too many errors, stop polling
        if (this.state.refreshCount > 10) { // After 10 failed attempts
            this.stopPolling();
            AudioTranscriber.utils.showToast('Status updates stopped due to repeated errors', 'warning', 8000);
        }
    },

    /**
     * Show results error
     * @param {string} message - Error message
     */
    showResultsError: function(message) {
        if (this.elements.transcriptText) {
            this.elements.transcriptText.textContent = `Error loading results: ${message}`;
            this.elements.transcriptText.classList.add('text-danger');
        }
    },

    /**
     * Show auto-refresh indicator
     */
    showAutoRefreshIndicator: function() {
        // Create or update indicator
        let indicator = document.getElementById('autoRefreshIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'autoRefreshIndicator';
            indicator.className = 'auto-refresh-indicator';
            document.body.appendChild(indicator);
        }
        
        indicator.textContent = `Auto-refreshing... (${this.state.refreshCount}/${this.config.maxPollAttempts})`;
        
        // Auto-hide after 2 seconds
        setTimeout(() => {
            if (indicator && indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 2000);
    },

    /**
     * Show message when auto-refresh is stopped
     */
    showAutoRefreshStopped: function() {
        AudioTranscriber.utils.showToast(
            'Auto-refresh stopped after maximum attempts. Use the refresh button to check status manually.',
            'info',
            8000
        );
    }
};

// Initialize when DOM is ready (handled in template)
// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioTranscriber.status;
}