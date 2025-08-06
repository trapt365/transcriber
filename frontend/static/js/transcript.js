/**
 * Transcript Display and Interaction JavaScript
 * Handles transcript loading, display modes, search, and user interactions
 */

class TranscriptManager {
    constructor() {
        this.jobData = null;
        this.transcriptData = null;
        this.currentDisplayMode = 'full';
        this.searchResults = [];
        this.currentSearchIndex = 0;
        this.speakerColors = [
            'speaker-1', 'speaker-2', 'speaker-3', 
            'speaker-4', 'speaker-5', 'speaker-6'
        ];
        
        this.init();
    }
    
    init() {
        this.loadJobData();
        this.bindEvents();
        this.initializeDownloadModal();
        this.loadTranscript();
    }
    
    loadJobData() {
        try {
            const jobDataElement = document.getElementById('jobData');
            if (jobDataElement) {
                this.jobData = JSON.parse(jobDataElement.textContent);
            }
        } catch (error) {
            console.error('Error loading job data:', error);
            this.showError('Failed to load job information');
        }
    }
    
    bindEvents() {
        // Display mode toggles
        const displayModeInputs = document.querySelectorAll('input[name="displayMode"]');
        displayModeInputs.forEach(input => {
            input.addEventListener('change', () => {
                if (input.checked) {
                    this.switchDisplayMode(input.value);
                }
            });
        });
        
        // Speaker highlighting toggle
        const highlightToggle = document.getElementById('highlightSpeakers');
        if (highlightToggle) {
            highlightToggle.addEventListener('change', () => {
                this.toggleSpeakerHighlighting(highlightToggle.checked);
            });
        }
        
        // Action buttons
        document.getElementById('copyTranscriptBtn')?.addEventListener('click', () => {
            this.copyTranscript();
        });
        
        document.getElementById('downloadTranscriptBtn')?.addEventListener('click', () => {
            this.downloadTranscript();
        });
        
        document.getElementById('refreshTranscriptBtn')?.addEventListener('click', () => {
            this.refreshTranscript();
        });
        
        // Search functionality
        document.getElementById('searchBtn')?.addEventListener('click', () => {
            this.toggleSearch();
        });
        
        document.getElementById('searchInput')?.addEventListener('input', (e) => {
            this.performSearch(e.target.value);
        });
        
        document.getElementById('clearSearchBtn')?.addEventListener('click', () => {
            this.clearSearch();
        });
        
        // Preview toggle
        document.getElementById('togglePreview')?.addEventListener('click', () => {
            this.togglePreview();
        });
        
        // Retry button
        document.getElementById('retryBtn')?.addEventListener('click', () => {
            this.loadTranscript();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'c':
                        if (e.target.closest('.transcript-content')) {
                            // Allow normal copy behavior within transcript
                            return;
                        }
                        break;
                    case 'f':
                        e.preventDefault();
                        this.toggleSearch();
                        break;
                    case 's':
                        e.preventDefault();
                        this.downloadTranscript();
                        break;
                }
            }
            
            if (e.key === 'Escape') {
                this.clearSearch();
            }
        });
    }
    
    async loadTranscript() {
        if (!this.jobData?.api_endpoint) {
            this.showError('Missing API endpoint information');
            return;
        }
        
        this.showLoading();
        
        try {
            const response = await fetch(this.jobData.api_endpoint);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to load transcript');
            }
            
            if (!data.success) {
                throw new Error(data.message || 'Transcript data is invalid');
            }
            
            this.transcriptData = data;
            this.renderTranscript();
            this.showValidationWarnings();
            this.hideLoading();
            
        } catch (error) {
            console.error('Error loading transcript:', error);
            this.showError(error.message || 'Failed to load transcript');
        }
    }
    
    renderTranscript() {
        if (!this.transcriptData) return;
        
        const transcript = this.transcriptData.transcript;
        
        // Update overview stats
        this.updateOverviewStats(transcript);
        
        // Render preview
        this.renderPreview(transcript.preview);
        
        // Render main content based on current display mode
        this.renderCurrentView();
    }
    
    updateOverviewStats(transcript) {
        document.getElementById('speakerCount').textContent = transcript.speaker_count || '0';
        document.getElementById('segmentCount').textContent = transcript.total_segments || '0';
        document.getElementById('totalDuration').textContent = this.formatDuration(transcript.total_duration || 0);
        document.getElementById('confidenceScore').textContent = 
            transcript.confidence_score ? `${Math.round(transcript.confidence_score * 100)}%` : 'N/A';
    }
    
    renderPreview(previewText) {
        const previewElement = document.getElementById('transcriptPreview');
        if (previewElement && previewText) {
            previewElement.textContent = previewText;
            this.applyCyrillicFont(previewElement);
        }
    }
    
    renderCurrentView() {
        switch (this.currentDisplayMode) {
            case 'full':
                this.renderFullTranscript();
                break;
            case 'segments':
                this.renderSegmentsView();
                break;
            case 'speakers':
                this.renderSpeakersView();
                break;
        }
    }
    
    renderFullTranscript() {
        const container = document.getElementById('fullTranscriptContent');
        const transcript = this.transcriptData.transcript;
        
        if (!container || !transcript.formatted_text) return;
        
        // Apply speaker highlighting to formatted text
        let formattedHtml = this.applyFullTranscriptFormatting(transcript.formatted_text);
        
        container.innerHTML = formattedHtml;
        this.applyCyrillicFont(container);
        
        document.getElementById('transcriptTitle').textContent = 'Full Transcript';
    }
    
    renderSegmentsView() {
        const container = document.getElementById('segmentsContainer');
        const segments = this.transcriptData.transcript.segments;
        
        if (!container || !segments) return;
        
        container.innerHTML = '';
        
        segments.forEach((segment, index) => {
            const segmentElement = this.createSegmentElement(segment, index);
            container.appendChild(segmentElement);
        });
        
        document.getElementById('transcriptTitle').textContent = 'Segments View';
    }
    
    renderSpeakersView() {
        const container = document.getElementById('speakersContainer');
        const segments = this.transcriptData.transcript.segments;
        
        if (!container || !segments) return;
        
        container.innerHTML = '';
        
        // Group segments by speaker
        const speakerGroups = {};
        segments.forEach(segment => {
            const speaker = segment.speaker || 'Unknown Speaker';
            if (!speakerGroups[speaker]) {
                speakerGroups[speaker] = [];
            }
            speakerGroups[speaker].push(segment);
        });
        
        // Render each speaker section
        Object.entries(speakerGroups).forEach(([speaker, speakerSegments]) => {
            const speakerElement = this.createSpeakerSection(speaker, speakerSegments);
            container.appendChild(speakerElement);
        });
        
        document.getElementById('transcriptTitle').textContent = 'By Speaker';
    }
    
    applyFullTranscriptFormatting(text) {
        if (!text) return '';
        
        // Split by paragraphs (double newlines)
        const paragraphs = text.split('\n\n');
        
        return paragraphs.map(paragraph => {
            // Match pattern: [timestamp] Speaker: text
            const speakerMatch = paragraph.match(/^\[([^\]]+)\]\s*([^:]+):\s*(.+)/s);
            
            if (speakerMatch) {
                const [, timestamp, speaker, content] = speakerMatch;
                const speakerClass = this.getSpeakerClass(speaker);
                const highlightClass = document.getElementById('highlightSpeakers')?.checked ? 
                    `speaker-highlight ${speakerClass}` : '';
                
                return `
                    <div class="${highlightClass}">
                        <span class="timestamp">${timestamp}</span>
                        <span class="speaker-label ${speakerClass}">${speaker}:</span>
                        <span class="transcript-text">${content.trim()}</span>
                    </div>
                `;
            }
            
            return `<div class="transcript-text">${paragraph}</div>`;
        }).join('\n');
    }
    
    createSegmentElement(segment, index) {
        const div = document.createElement('div');
        div.className = 'segment-item';
        
        const speakerClass = this.getSpeakerClass(segment.speaker);
        const confidenceClass = this.getConfidenceClass(segment.confidence_score);
        
        div.innerHTML = `
            <div class="segment-header">
                <span class="timestamp">${this.formatTime(segment.start_time)}</span>
                <span class="speaker-label ${speakerClass}">${segment.speaker || 'Unknown'}</span>
            </div>
            <div class="segment-text">${segment.text || ''}</div>
            <div class="segment-meta">
                <span>Duration: ${this.formatDuration((segment.end_time || 0) - (segment.start_time || 0))}</span>
                ${segment.confidence_score ? `<span class="segment-confidence ${confidenceClass}">
                    Confidence: ${Math.round(segment.confidence_score * 100)}%
                </span>` : ''}
            </div>
        `;
        
        this.applyCyrillicFont(div.querySelector('.segment-text'));
        return div;
    }
    
    createSpeakerSection(speaker, segments) {
        const section = document.createElement('div');
        section.className = 'speaker-section';
        
        const speakerClass = this.getSpeakerClass(speaker);
        const totalDuration = segments.reduce((sum, seg) => 
            sum + ((seg.end_time || 0) - (seg.start_time || 0)), 0);
        
        section.innerHTML = `
            <div class="speaker-header">
                <h5 class="speaker-name ${speakerClass}">${speaker}</h5>
                <div class="speaker-stats">
                    <span>${segments.length} segments</span>
                    <span>${this.formatDuration(totalDuration)} total</span>
                </div>
            </div>
            <div class="speaker-content">
                ${segments.map((segment, index) => `
                    <div class="speaker-segment">
                        <span class="timestamp">${this.formatTime(segment.start_time)}</span>
                        <div class="segment-text">${segment.text || ''}</div>
                    </div>
                `).join('')}
            </div>
        `;
        
        // Apply Cyrillic font to all segment texts
        const segmentTexts = section.querySelectorAll('.segment-text');
        segmentTexts.forEach(text => this.applyCyrillicFont(text));
        
        return section;
    }
    
    getSpeakerClass(speaker) {
        if (!speaker) return 'speaker-1';
        
        // Extract number from speaker name if possible
        const match = speaker.match(/(\d+)/);
        if (match) {
            const num = parseInt(match[1]);
            return this.speakerColors[(num - 1) % this.speakerColors.length];
        }
        
        // Fallback: use hash of speaker name
        let hash = 0;
        for (let i = 0; i < speaker.length; i++) {
            hash = ((hash << 5) - hash + speaker.charCodeAt(i)) & 0xffffffff;
        }
        return this.speakerColors[Math.abs(hash) % this.speakerColors.length];
    }
    
    getConfidenceClass(confidence) {
        if (!confidence) return '';
        if (confidence >= 0.8) return 'high';
        if (confidence >= 0.6) return 'medium';
        return 'low';
    }
    
    switchDisplayMode(mode) {
        this.currentDisplayMode = mode;
        
        // Hide all views
        document.getElementById('fullTranscriptView').style.display = 'none';
        document.getElementById('segmentsView').style.display = 'none';
        document.getElementById('speakersView').style.display = 'none';
        
        // Show selected view
        switch (mode) {
            case 'full':
                document.getElementById('fullTranscriptView').style.display = 'block';
                break;
            case 'segments':
                document.getElementById('segmentsView').style.display = 'block';
                break;
            case 'speakers':
                document.getElementById('speakersView').style.display = 'block';
                break;
        }
        
        this.renderCurrentView();
    }
    
    toggleSpeakerHighlighting(enabled) {
        const highlights = document.querySelectorAll('.speaker-highlight');
        highlights.forEach(el => {
            if (enabled) {
                el.style.display = 'block';
            } else {
                el.classList.remove('speaker-highlight');
                el.classList.add('no-highlight');
            }
        });
        
        // Re-render current view to apply highlighting changes
        this.renderCurrentView();
    }
    
    toggleSearch() {
        const searchBox = document.getElementById('searchBox');
        const searchInput = document.getElementById('searchInput');
        
        if (searchBox.style.display === 'none' || !searchBox.style.display) {
            searchBox.style.display = 'block';
            searchInput?.focus();
        } else {
            searchBox.style.display = 'none';
            this.clearSearch();
        }
    }
    
    performSearch(query) {
        if (!query.trim()) {
            this.clearSearchHighlights();
            document.getElementById('searchResults').textContent = 'Enter text to search';
            return;
        }
        
        this.clearSearchHighlights();
        
        const searchRegex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        const transcriptContainers = document.querySelectorAll('.transcript-text, .segment-text');
        
        this.searchResults = [];
        let totalMatches = 0;
        
        transcriptContainers.forEach(container => {
            const originalText = container.textContent;
            let highlightedText = originalText;
            let match;
            
            // Reset regex lastIndex
            searchRegex.lastIndex = 0;
            
            while ((match = searchRegex.exec(originalText)) !== null) {
                totalMatches++;
                this.searchResults.push({
                    element: container,
                    index: totalMatches - 1
                });
            }
            
            // Apply highlights
            highlightedText = originalText.replace(searchRegex, 
                '<span class="search-highlight">$&</span>'
            );
            
            container.innerHTML = highlightedText;
        });
        
        if (totalMatches > 0) {
            document.getElementById('searchResults').textContent = 
                `Found ${totalMatches} matches`;
            this.highlightCurrentSearchResult(0);
        } else {
            document.getElementById('searchResults').textContent = 'No matches found';
        }
    }
    
    clearSearch() {
        document.getElementById('searchInput').value = '';
        this.clearSearchHighlights();
        document.getElementById('searchResults').textContent = 'Enter text to search';
        document.getElementById('searchBox').style.display = 'none';
    }
    
    clearSearchHighlights() {
        const highlights = document.querySelectorAll('.search-highlight');
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
            parent.normalize();
        });
        
        this.searchResults = [];
        this.currentSearchIndex = 0;
    }
    
    highlightCurrentSearchResult(index) {
        const highlights = document.querySelectorAll('.search-highlight');
        highlights.forEach((highlight, i) => {
            if (i === index) {
                highlight.classList.add('current');
                highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                highlight.classList.remove('current');
            }
        });
    }
    
    togglePreview() {
        const previewBody = document.getElementById('previewBody');
        const toggleBtn = document.getElementById('togglePreview');
        const icon = toggleBtn.querySelector('i');
        
        if (previewBody.style.display === 'none') {
            previewBody.style.display = 'block';
            icon.className = 'bi bi-chevron-up';
        } else {
            previewBody.style.display = 'none';
            icon.className = 'bi bi-chevron-down';
        }
    }
    
    async copyTranscript() {
        if (!this.transcriptData?.transcript?.formatted_text) {
            this.showToast('No transcript available to copy', 'error');
            return;
        }
        
        try {
            await navigator.clipboard.writeText(this.transcriptData.transcript.formatted_text);
            this.showToast('Transcript copied to clipboard', 'success');
        } catch (error) {
            console.error('Error copying transcript:', error);
            
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = this.transcriptData.transcript.formatted_text;
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.showToast('Transcript copied to clipboard', 'success');
            } catch (fallbackError) {
                this.showToast('Failed to copy transcript', 'error');
            }
            
            document.body.removeChild(textArea);
        }
    }
    
    /**
     * Initialize download modal functionality
     */
    initializeDownloadModal() {
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
    }

    /**
     * Check export format availability
     */
    checkExportAvailability() {
        // Check if we have segments for timed formats
        const hasSegments = this.transcriptData?.transcript?.segments?.length > 0;
        
        const srtFormat = document.getElementById('srtFormat');
        const vttFormat = document.getElementById('vttFormat');
        
        if (!hasSegments) {
            srtFormat?.classList.add('disabled');
            vttFormat?.classList.add('disabled');
        } else {
            srtFormat?.classList.remove('disabled');
            vttFormat?.classList.remove('disabled');
        }
    }

    /**
     * Download transcript in specified format
     */
    downloadInFormat(format) {
        const downloadProgress = document.getElementById('downloadProgress');
        const modal = bootstrap.Modal.getInstance(document.getElementById('downloadModal'));
        
        // Show progress
        downloadProgress.style.display = 'block';
        
        // Make API request to export endpoint
        const exportUrl = `/api/v1/jobs/${this.jobData.job_id}/export/${format}`;
        
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
                const filename = `transcript_${this.jobData.job_id}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format}`;
                
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                URL.revokeObjectURL(url);
                
                // Hide progress and close modal
                downloadProgress.style.display = 'none';
                modal.hide();
                
                this.showToast(`Transcript downloaded as ${format.toUpperCase()}`, 'success');
            })
            .catch(error => {
                console.error('Download error:', error);
                downloadProgress.style.display = 'none';
                this.showToast(`Download failed: ${error.message}`, 'error');
            });
    }

    downloadTranscript() {
        // Open download modal instead of direct download
        const modal = new bootstrap.Modal(document.getElementById('downloadModal'));
        modal.show();
    }
    
    refreshTranscript() {
        const refreshBtn = document.getElementById('refreshTranscriptBtn');
        const icon = refreshBtn.querySelector('i');
        
        icon.style.animation = 'spin 1s linear infinite';
        this.loadTranscript().finally(() => {
            icon.style.animation = '';
        });
    }
    
    showValidationWarnings() {
        const validation = this.transcriptData?.validation;
        if (!validation?.warnings || validation.warnings.length === 0) {
            return;
        }
        
        const warningsContainer = document.getElementById('validationWarnings');
        const warningsList = document.getElementById('warningsList');
        
        if (warningsContainer && warningsList) {
            warningsList.innerHTML = validation.warnings.map(warning => 
                `<li>${warning}</li>`
            ).join('');
            
            warningsContainer.style.display = 'block';
        }
    }
    
    applyCyrillicFont(element) {
        if (!element) return;
        
        // Check if text contains Cyrillic characters
        const cyrillicRegex = /[\u0400-\u04FF]/;
        if (cyrillicRegex.test(element.textContent)) {
            element.classList.add('cyrillic-text');
        }
    }
    
    formatTime(seconds) {
        if (!seconds && seconds !== 0) return '--:--';
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        
        if (seconds >= 3600) {
            const hours = Math.floor(seconds / 3600);
            return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatDuration(seconds) {
        if (!seconds && seconds !== 0) return '0s';
        
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        }
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        
        if (seconds < 3600) {
            return `${mins}m${secs > 0 ? ` ${secs}s` : ''}`;
        }
        
        const hours = Math.floor(seconds / 3600);
        const remainingMins = mins % 60;
        
        return `${hours}h${remainingMins > 0 ? ` ${remainingMins}m` : ''}`;
    }
    
    showLoading() {
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('transcriptContent').style.display = 'none';
        document.getElementById('errorState').style.display = 'none';
    }
    
    hideLoading() {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('transcriptContent').style.display = 'block';
        document.getElementById('errorState').style.display = 'none';
    }
    
    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').style.display = 'block';
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('transcriptContent').style.display = 'none';
    }
    
    showToast(message, type = 'success') {
        const toast = document.getElementById('successToast');
        const messageEl = document.getElementById('successMessage');
        
        if (toast && messageEl) {
            messageEl.textContent = message;
            
            // Update toast styling based on type
            const header = toast.querySelector('.toast-header');
            const icon = header.querySelector('i');
            
            header.className = `toast-header text-white bg-${type === 'error' ? 'danger' : 'success'}`;
            icon.className = `bi bi-${type === 'error' ? 'exclamation-triangle' : 'check-circle'} me-2`;
            
            const toastInstance = new bootstrap.Toast(toast);
            toastInstance.show();
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new TranscriptManager();
});

// Add CSS animation for refresh button
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);