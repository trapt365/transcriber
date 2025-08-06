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
        refreshCount: 0,
        // WebSocket state
        socket: null,
        isConnected: false,
        reconnectAttempts: 0,
        retryTimeout: null,
        usingWebSocket: false
    },

    // Configuration
    config: {
        pollIntervalMs: 3000, // 3 seconds
        maxPollAttempts: 200, // ~10 minutes max polling
        refreshTimeout: 30000, // 30 seconds timeout for requests
        useWebSocket: true, // Use WebSocket if available
        maxReconnectAttempts: 5 // Max WebSocket reconnection attempts
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
        
        // Initialize download modal
        this.initializeDownloadModal();
        
        // Load stored status first
        this.loadStoredStatus();

        // Initialize WebSocket or fallback to polling
        if (this.config.useWebSocket && this.initializeWebSocket()) {
            console.log('Using WebSocket for real-time updates');
            this.state.usingWebSocket = true;
        } else {
            console.log('Falling back to polling');
            // Start initial status check
            this.updateStatus();
            
            // Start polling if job is not completed
            if (this.shouldPoll(this.state.currentStatus)) {
                this.startPolling();
            }
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
            if (!document.hidden) {
                if (this.state.usingWebSocket && !this.state.isConnected) {
                    // Try to reconnect WebSocket
                    this.scheduleReconnect();
                } else if (!this.state.usingWebSocket && this.shouldPoll(this.state.currentStatus)) {
                    this.updateStatus();
                    if (!this.state.isPolling) {
                        this.startPolling();
                    }
                }
            }
        });

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
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
        
        // Store current job data for export functionality
        this.currentJobData = { result: result };
        
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
     * Initialize download modal functionality
     */
    initializeDownloadModal: function() {
        const modal = document.getElementById('downloadModal');
        const formatCards = modal.querySelectorAll('.export-format-card');
        const confirmBtn = document.getElementById('confirmDownloadBtn');
        const formatInfo = document.getElementById('formatInfo');
        const formatInfoText = document.getElementById('formatInfoText');
        let selectedFormat = null;

        // Format information
        const formatDescriptions = {
            txt: 'Plain text file with speaker labels and timestamps. Best for general reading and editing.',
            json: 'Structured data format containing all metadata, speakers, segments, and timing information.',
            srt: 'Standard subtitle format for video editing. Requires segment timing data.',
            vtt: 'Web Video Text Tracks format for web players. Requires segment timing data.',
            csv: 'Spreadsheet format with segment-by-segment data. Great for analysis and data processing.'
        };

        // Handle format selection
        formatCards.forEach(card => {
            card.addEventListener('click', () => {
                // Check if format is disabled
                if (card.classList.contains('disabled')) {
                    return;
                }

                // Remove previous selection
                formatCards.forEach(c => c.classList.remove('selected'));
                
                // Select current format
                card.classList.add('selected');
                selectedFormat = card.dataset.format;
                
                // Update format info
                formatInfoText.textContent = formatDescriptions[selectedFormat];
                formatInfo.style.display = 'block';
                
                // Enable confirm button
                confirmBtn.disabled = false;
            });
        });

        // Handle confirm download
        confirmBtn.addEventListener('click', () => {
            if (selectedFormat) {
                this.downloadInFormat(selectedFormat);
            }
        });

        // Reset modal when opened
        modal.addEventListener('show.bs.modal', () => {
            this.checkExportAvailability();
            // Reset selection
            formatCards.forEach(c => c.classList.remove('selected'));
            selectedFormat = null;
            confirmBtn.disabled = true;
            formatInfo.style.display = 'none';
        });
    },

    /**
     * Check export format availability
     */
    checkExportAvailability: function() {
        // Check if we have segments for timed formats
        const hasSegments = this.currentJobData?.result?.segments?.length > 0;
        
        const srtFormat = document.getElementById('srtFormat');
        const vttFormat = document.getElementById('vttFormat');
        
        if (!hasSegments) {
            srtFormat?.classList.add('disabled');
            vttFormat?.classList.add('disabled');
        } else {
            srtFormat?.classList.remove('disabled');
            vttFormat?.classList.remove('disabled');
        }
    },

    /**
     * Download transcript in specified format
     */
    downloadInFormat: function(format) {
        const downloadProgress = document.getElementById('downloadProgress');
        const modal = bootstrap.Modal.getInstance(document.getElementById('downloadModal'));
        
        // Show progress
        downloadProgress.style.display = 'block';
        
        // Make API request to export endpoint
        const exportUrl = `/api/v1/jobs/${this.state.jobId}/export/${format}`;
        
        fetch(exportUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Export failed: ${response.status} ${response.statusText}`);
                }
                return response.blob();
            })
            .then(blob => {
                // Create download link
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                
                // Get filename from response header or generate one
                const filename = `transcript_${this.state.jobId}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format}`;
                
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                URL.revokeObjectURL(url);
                
                // Hide progress and close modal
                downloadProgress.style.display = 'none';
                modal.hide();
                
                AudioTranscriber.utils.showToast(`Transcript downloaded as ${format.toUpperCase()}`, 'success', 3000);
            })
            .catch(error => {
                console.error('Download error:', error);
                downloadProgress.style.display = 'none';
                AudioTranscriber.utils.showToast(`Download failed: ${error.message}`, 'error', 5000);
            });
    },

    /**
     * Legacy download function for backward compatibility
     */
    downloadTranscript: function() {
        // Open download modal instead of direct download
        const modal = new bootstrap.Modal(document.getElementById('downloadModal'));
        modal.show();
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
    },

    /**
     * Initialize WebSocket connection
     * @returns {boolean} True if WebSocket was successfully initialized
     */
    initializeWebSocket: function() {
        try {
            // Check if io (Socket.IO) is available
            if (typeof io === 'undefined') {
                console.log('Socket.IO not available, falling back to polling');
                return false;
            }

            // Initialize Socket.IO connection
            this.state.socket = io();
            
            this.state.socket.on('connect', () => {
                console.log('WebSocket connected');
                this.state.isConnected = true;
                this.state.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
                this.subscribeToJobStatus();
            });
            
            this.state.socket.on('disconnect', () => {
                console.log('WebSocket disconnected');
                this.state.isConnected = false;
                this.updateConnectionStatus(false);
                this.scheduleReconnect();
            });
            
            this.state.socket.on('job_status_update', (data) => {
                console.log('Real-time status update received:', data);
                this.handleWebSocketStatusUpdate(data);
            });
            
            this.state.socket.on('queue_position_update', (data) => {
                console.log('Queue position update:', data);
                this.handleQueueUpdate(data);
            });
            
            this.state.socket.on('processing_error', (data) => {
                console.log('Processing error:', data);
                this.handleProcessingError(data);
            });
            
            this.state.socket.on('error', (error) => {
                console.error('WebSocket error:', error);
                this.handleConnectionError(error);
            });
            
            return true;
            
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            return false;
        }
    },

    /**
     * Subscribe to job status updates via WebSocket
     */
    subscribeToJobStatus: function() {
        if (this.state.socket && this.state.isConnected && this.state.jobId) {
            this.state.socket.emit('subscribe_job_status', { job_id: this.state.jobId });
        }
    },

    /**
     * Schedule WebSocket reconnection
     */
    scheduleReconnect: function() {
        if (this.state.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.state.reconnectAttempts++;
            const delay = 1000 * Math.pow(2, this.state.reconnectAttempts - 1); // Exponential backoff
            
            console.log(`Scheduling WebSocket reconnect attempt ${this.state.reconnectAttempts} in ${delay}ms`);
            
            this.state.retryTimeout = setTimeout(() => {
                if (this.state.socket) {
                    this.state.socket.connect();
                }
            }, delay);
        } else {
            console.log('Max WebSocket reconnect attempts reached, falling back to polling');
            this.fallbackToPolling();
        }
    },

    /**
     * Fallback to polling when WebSocket fails
     */
    fallbackToPolling: function() {
        console.log('Switching to polling mode');
        this.state.usingWebSocket = false;
        this.updateConnectionStatus('polling');
        
        // Disconnect WebSocket if still connected
        if (this.state.socket) {
            this.state.socket.disconnect();
        }
        
        // Start polling
        this.updateStatus();
        if (this.shouldPoll(this.state.currentStatus)) {
            this.startPolling();
        }
    },

    /**
     * Handle WebSocket status update
     * @param {object} data - Status update data
     */
    handleWebSocketStatusUpdate: function(data) {
        if (data.job_id !== this.state.jobId) {
            return; // Ignore updates for other jobs
        }

        // Store in local storage
        this.storeStatus(data);

        // Convert WebSocket data format to match polling format
        const jobData = {
            status: data.status,
            progress: data.progress || 0,
            processing_phase: data.processing_phase,
            estimated_completion: data.estimated_completion,
            queue_position: data.queue_position,
            can_cancel: data.can_cancel,
            error_message: data.error_message
        };

        this.handleStatusUpdate(jobData);
    },

    /**
     * Handle queue position update
     * @param {object} data - Queue update data
     */
    handleQueueUpdate: function(data) {
        if (data.job_id !== this.state.jobId) {
            return;
        }

        // Update queue position display
        this.updateQueuePosition(data.queue_position, data.estimated_wait_seconds);
    },

    /**
     * Handle processing error
     * @param {object} data - Error data
     */
    handleProcessingError: function(data) {
        if (data.job_id !== this.state.jobId) {
            return;
        }

        this.showProcessingError(data.error_message, data.suggested_actions);
    },

    /**
     * Handle connection error
     * @param {object} error - Error data
     */
    handleConnectionError: function(error) {
        console.error('WebSocket connection error:', error);
        AudioTranscriber.utils.showToast('Connection error. Attempting to reconnect...', 'warning', 3000);
    },

    /**
     * Update connection status display
     * @param {boolean|string} status - Connection status
     */
    updateConnectionStatus: function(status) {
        let indicator = document.getElementById('connection-status');
        
        if (!indicator) {
            // Create connection status indicator
            indicator = document.createElement('div');
            indicator.id = 'connection-status';
            indicator.className = 'connection-status';
            
            // Insert into status page
            const statusContainer = document.querySelector('.job-status-container');
            if (statusContainer) {
                statusContainer.insertBefore(indicator, statusContainer.firstChild);
            }
        }

        if (status === true) {
            indicator.textContent = '🟢 Connected';
            indicator.className = 'connection-status connected';
        } else if (status === 'polling') {
            indicator.textContent = '🔄 Polling';
            indicator.className = 'connection-status polling';
        } else {
            indicator.textContent = '🔴 Disconnected';
            indicator.className = 'connection-status disconnected';
        }
    },

    /**
     * Update queue position display
     * @param {number} position - Queue position
     * @param {number} estimatedWait - Estimated wait time in seconds
     */
    updateQueuePosition: function(position, estimatedWait) {
        let queueElement = document.getElementById('queue-position');
        
        if (!queueElement) {
            // Create queue position element
            queueElement = document.createElement('div');
            queueElement.id = 'queue-position';
            queueElement.className = 'queue-position alert alert-info';
            
            // Insert into processing section
            const processingSection = this.elements.processingSection;
            if (processingSection) {
                processingSection.appendChild(queueElement);
            }
        }

        if (position > 1) {
            let message = `Position in queue: ${position}`;
            
            if (estimatedWait) {
                const waitTime = AudioTranscriber.utils.formatDuration(estimatedWait);
                message += ` • Estimated wait: ${waitTime}`;
            }
            
            queueElement.textContent = message;
            queueElement.style.display = 'block';
        } else {
            queueElement.style.display = 'none';
        }
    },

    /**
     * Show processing error with suggested actions
     * @param {string} message - Error message
     * @param {Array} suggestedActions - Suggested actions
     */
    showProcessingError: function(message, suggestedActions = []) {
        // Show main error
        if (this.elements.errorMessage) {
            this.elements.errorMessage.textContent = message;
        }
        
        // Show suggested actions if available
        if (suggestedActions.length > 0) {
            let actionsElement = document.getElementById('suggested-actions');
            
            if (!actionsElement) {
                actionsElement = document.createElement('div');
                actionsElement.id = 'suggested-actions';
                actionsElement.className = 'suggested-actions mt-3';
                
                if (this.elements.errorSection) {
                    this.elements.errorSection.appendChild(actionsElement);
                }
            }
            
            const actionsList = suggestedActions.map(action => `<li>${action}</li>`).join('');
            actionsElement.innerHTML = `
                <h5>Suggested Actions:</h5>
                <ul>${actionsList}</ul>
            `;
            actionsElement.style.display = 'block';
        }
        
        AudioTranscriber.utils.showToast('Processing error: ' + message, 'error', 5000);
    },

    /**
     * Store status in local storage
     * @param {object} data - Status data
     */
    storeStatus: function(data) {
        try {
            localStorage.setItem(`job_status_${this.state.jobId}`, JSON.stringify({
                ...data,
                timestamp: Date.now()
            }));
        } catch (error) {
            console.error('Error storing status:', error);
        }
    },

    /**
     * Load stored status from local storage
     */
    loadStoredStatus: function() {
        try {
            const stored = localStorage.getItem(`job_status_${this.state.jobId}`);
            if (stored) {
                const data = JSON.parse(stored);
                // Only use if less than 30 seconds old
                if (Date.now() - data.timestamp < 30000) {
                    console.log('Loading stored status:', data);
                    this.handleWebSocketStatusUpdate(data);
                }
            }
        } catch (error) {
            console.error('Error loading stored status:', error);
        }
    },

    /**
     * Cleanup WebSocket connection
     */
    cleanup: function() {
        // Clear timeouts
        if (this.state.retryTimeout) {
            clearTimeout(this.state.retryTimeout);
        }
        
        // Disconnect WebSocket
        if (this.state.socket) {
            if (this.state.isConnected) {
                this.state.socket.emit('unsubscribe_job_status', { job_id: this.state.jobId });
            }
            this.state.socket.disconnect();
        }
        
        // Stop polling
        this.stopPolling();
    }
};

// Initialize when DOM is ready (handled in template)
// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioTranscriber.status;
}