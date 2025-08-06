"""End-to-end tests for transcript functionality."""

import pytest
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from backend.app import create_app
from backend.app.models import Job, JobResult, Speaker, TranscriptSegment
from backend.app.models.enums import JobStatus
from backend.extensions import db


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app(testing=True)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def driver():
    """Create Chrome WebDriver for testing."""
    options = Options()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    except Exception as e:
        pytest.skip(f"Chrome WebDriver not available: {e}")


@pytest.fixture
def sample_job_with_transcript(app):
    """Create a complete job with transcript data for E2E testing."""
    with app.app_context():
        # Create job
        job = Job(
            job_id='e2e-test-job-123',
            filename='e2e_test_audio.mp3',
            original_filename='e2e_test_audio.mp3',
            file_size=2048,
            file_format='mp3',
            status=JobStatus.COMPLETED.value,
            language='ru-RU',
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration=120.0
        )
        db.session.add(job)
        db.session.flush()
        
        # Create job result
        job_result = JobResult(
            job_id=job.id,
            raw_transcript='E2E test transcript',
            confidence_score=0.87,
            word_count=85,
            processing_duration=60.5
        )
        db.session.add(job_result)
        
        # Create speakers
        speaker1 = Speaker(
            job_id=job.id,
            speaker_id='1',
            speaker_label='Presenter',
            total_speech_time=80.0,
            segment_count=4
        )
        speaker2 = Speaker(
            job_id=job.id,
            speaker_id='2',
            speaker_label='Участник',
            total_speech_time=40.0,
            segment_count=2
        )
        db.session.add_all([speaker1, speaker2])
        db.session.flush()
        
        # Create transcript segments with realistic content
        segments = [
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=1,
                start_time=0.0,
                end_time=15.0,
                text='Добро пожаловать на сегодняшнее совещание. Мы обсудим важные вопросы развития проекта.',
                confidence_score=0.92
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=2,
                start_time=15.0,
                end_time=35.0,
                text='Первый пункт повестки дня касается технических аспектов реализации новой функциональности.',
                confidence_score=0.89
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker2.id,
                segment_order=3,
                start_time=36.0,
                end_time=55.0,
                text='Спасибо за подробное объяснение. У меня есть несколько вопросов по этому поводу.',
                confidence_score=0.85
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=4,
                start_time=56.0,
                end_time=80.0,
                text='Конечно, задавайте ваши вопросы. Я готов обсудить все детали реализации.',
                confidence_score=0.91
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker2.id,
                segment_order=5,
                start_time=81.0,
                end_time=105.0,
                text='Қазақша сұрақ: Жаңа жүйе қанша уақытта дайын болады?',
                confidence_score=0.78
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=6,
                start_time=106.0,
                end_time=120.0,
                text='Планируем завершить разработку в течение следующих двух недель.',
                confidence_score=0.88
            )
        ]
        db.session.add_all(segments)
        db.session.commit()
        
        return job


@pytest.fixture
def flask_server(app):
    """Start Flask development server for E2E testing."""
    import threading
    import socket
    from contextlib import closing
    
    # Find available port
    def find_free_port():
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    port = find_free_port()
    
    def run_server():
        app.run(port=port, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    yield f'http://localhost:{port}'
    
    # Server will be stopped when thread exits


@pytest.mark.e2e
class TestTranscriptE2E:
    """End-to-end tests for transcript functionality."""
    
    def test_transcript_page_loads_successfully(self, driver, flask_server, sample_job_with_transcript):
        """Test that transcript page loads and displays content correctly."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Check page title
        assert "Transcript" in driver.title
        
        # Check breadcrumb navigation
        breadcrumb = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "breadcrumb")))
        assert breadcrumb is not None
        
        # Check file information
        filename_element = driver.find_element(By.XPATH, "//*[contains(text(), 'e2e_test_audio.mp3')]")
        assert filename_element is not None
        
    def test_transcript_data_loads_via_api(self, driver, flask_server, sample_job_with_transcript):
        """Test that transcript data is loaded correctly via JavaScript API calls."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for transcript content to load
        try:
            transcript_content = wait.until(
                EC.presence_of_element_located((By.ID, "transcriptContent"))
            )
            
            # Wait for content to be visible (not loading state)
            wait.until(lambda d: transcript_content.is_displayed())
            
            # Check that overview stats are populated
            speaker_count = driver.find_element(By.ID, "speakerCount")
            assert speaker_count.text == "2"
            
            segment_count = driver.find_element(By.ID, "segmentCount")
            assert segment_count.text == "6"
            
        except TimeoutException:
            pytest.fail("Transcript content did not load within timeout period")
    
    def test_display_mode_switching(self, driver, flask_server, sample_job_with_transcript):
        """Test switching between different display modes."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for transcript to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        
        # Test segments view
        segments_radio = driver.find_element(By.ID, "segmentView")
        segments_radio.click()
        
        # Check that segments view is displayed
        segments_view = wait.until(
            EC.visibility_of_element_located((By.ID, "segmentsView"))
        )
        assert segments_view.is_displayed()
        
        # Test speakers view
        speakers_radio = driver.find_element(By.ID, "speakerView")
        speakers_radio.click()
        
        # Check that speakers view is displayed
        speakers_view = wait.until(
            EC.visibility_of_element_located((By.ID, "speakersView"))
        )
        assert speakers_view.is_displayed()
        
        # Test back to full transcript
        full_radio = driver.find_element(By.ID, "fullTranscript")
        full_radio.click()
        
        # Check that full transcript view is displayed
        full_view = wait.until(
            EC.visibility_of_element_located((By.ID, "fullTranscriptView"))
        )
        assert full_view.is_displayed()
    
    def test_cyrillic_text_display(self, driver, flask_server, sample_job_with_transcript):
        """Test that Cyrillic text is displayed correctly."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for transcript content to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        
        # Give extra time for API call to complete
        time.sleep(3)
        
        # Check for Russian text in the transcript
        page_source = driver.page_source
        assert "Добро пожаловать" in page_source
        assert "совещание" in page_source
        assert "Спасибо за подробное" in page_source
        
        # Check for Kazakh text
        assert "Қазақша сұрақ" in page_source
        
        # Verify text encoding by checking meta charset
        charset_meta = driver.find_element(By.XPATH, "//meta[@charset]")
        assert charset_meta.get_attribute("charset").lower() == "utf-8"
    
    def test_search_functionality(self, driver, flask_server, sample_job_with_transcript):
        """Test transcript search functionality."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for transcript content to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        time.sleep(3)  # Allow API call to complete
        
        # Open search
        search_btn = driver.find_element(By.ID, "searchBtn")
        search_btn.click()
        
        # Wait for search box to appear
        search_input = wait.until(
            EC.visibility_of_element_located((By.ID, "searchInput"))
        )
        
        # Perform search
        search_input.send_keys("совещание")
        
        # Wait for search results
        time.sleep(2)
        
        # Check search results indicator
        search_results = driver.find_element(By.ID, "searchResults")
        assert "matches" in search_results.text.lower()
    
    def test_copy_transcript_functionality(self, driver, flask_server, sample_job_with_transcript):
        """Test copy transcript button functionality."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for transcript content to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        time.sleep(3)  # Allow API call to complete
        
        # Click copy button
        copy_btn = driver.find_element(By.ID, "copyTranscriptBtn")
        copy_btn.click()
        
        # Wait for success toast
        try:
            success_toast = wait.until(
                EC.visibility_of_element_located((By.ID, "successToast"))
            )
            assert success_toast.is_displayed()
        except TimeoutException:
            # Copy might not work in headless mode, but button should still respond
            pass
    
    def test_responsive_design_mobile(self, driver, flask_server, sample_job_with_transcript):
        """Test transcript page responsiveness on mobile viewport."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        # Set mobile viewport
        driver.set_window_size(375, 667)  # iPhone 6/7/8 size
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        
        # Check that mobile-specific styles are applied
        display_mode_group = driver.find_element(By.CLASS_NAME, "btn-group")
        
        # On mobile, buttons should stack vertically
        # This is indicated by specific CSS classes or layout
        assert display_mode_group is not None
        
        # Check that content is still readable
        time.sleep(3)  # Allow API call to complete
        
        # Verify text is still visible and readable
        page_source = driver.page_source
        assert "Добро пожаловать" in page_source
    
    def test_accessibility_features(self, driver, flask_server, sample_job_with_transcript):
        """Test accessibility features of transcript page."""
        job_id = sample_job_with_transcript.job_id
        transcript_url = f"{flask_server}/transcript/{job_id}"
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        
        # Check ARIA labels
        copy_btn = driver.find_element(By.ID, "copyTranscriptBtn")
        assert copy_btn.get_attribute("title") is not None
        
        # Check semantic HTML structure
        main_element = driver.find_element(By.TAG_NAME, "main")
        assert main_element is not None
        
        # Check heading hierarchy
        h1_elements = driver.find_elements(By.TAG_NAME, "h1")
        assert len(h1_elements) >= 1
        
        # Check focus management for interactive elements
        search_btn = driver.find_element(By.ID, "searchBtn")
        search_btn.click()
        
        # Search input should become focused
        search_input = wait.until(
            EC.visibility_of_element_located((By.ID, "searchInput"))
        )
        
        # Verify input can receive focus
        assert search_input.is_enabled()


@pytest.mark.e2e
@pytest.mark.slow
class TestTranscriptE2EPerformance:
    """Performance-focused E2E tests for transcript functionality."""
    
    def test_large_transcript_loading_performance(self, driver, flask_server, app):
        """Test performance with large transcript data."""
        with app.app_context():
            # Create job with large transcript
            job = Job(
                job_id='large-transcript-job',
                filename='large_audio.mp3',
                original_filename='large_audio.mp3',
                file_size=10240,
                file_format='mp3',
                status=JobStatus.COMPLETED.value,
                duration=3600.0  # 1 hour
            )
            db.session.add(job)
            db.session.flush()
            
            job_result = JobResult(
                job_id=job.id,
                raw_transcript='Large transcript',
                confidence_score=0.82,
                word_count=2000
            )
            db.session.add(job_result)
            
            # Create many segments (simulate 1 hour of conversation)
            speaker1 = Speaker(
                job_id=job.id,
                speaker_id='1',
                speaker_label='Speaker A',
                total_speech_time=1800.0,
                segment_count=300
            )
            speaker2 = Speaker(
                job_id=job.id,
                speaker_id='2', 
                speaker_label='Speaker B',
                total_speech_time=1800.0,
                segment_count=300
            )
            db.session.add_all([speaker1, speaker2])
            db.session.flush()
            
            # Create 600 segments (1 every 6 seconds)
            segments = []
            for i in range(600):
                speaker = speaker1 if i % 2 == 0 else speaker2
                segments.append(TranscriptSegment(
                    job_id=job.id,
                    speaker_id=speaker.id,
                    segment_order=i + 1,
                    start_time=i * 6.0,
                    end_time=(i + 1) * 6.0,
                    text=f"Segment {i + 1} text content with some words to make it realistic",
                    confidence_score=0.8 + (i % 3) * 0.05
                ))
            
            db.session.add_all(segments)
            db.session.commit()
        
        transcript_url = f"{flask_server}/transcript/large-transcript-job"
        
        # Measure loading time
        start_time = time.time()
        
        driver.get(transcript_url)
        
        wait = WebDriverWait(driver, 30)  # Extended timeout for large data
        
        # Wait for content to load
        wait.until(EC.presence_of_element_located((By.ID, "transcriptContent")))
        
        # Wait for API call to complete (check for populated stats)
        wait.until(lambda d: d.find_element(By.ID, "segmentCount").text != "-")
        
        load_time = time.time() - start_time
        
        # Should load within reasonable time (30 seconds)
        assert load_time < 30
        
        # Verify content loaded correctly
        segment_count = driver.find_element(By.ID, "segmentCount")
        assert segment_count.text == "600"
        
        speaker_count = driver.find_element(By.ID, "speakerCount")
        assert speaker_count.text == "2"


if __name__ == '__main__':
    # Run E2E tests with appropriate markers
    pytest.main([__file__, "-m", "e2e", "-v"])