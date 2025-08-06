"""Tests for audio preprocessing service."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from backend.app.services.audio_service import AudioService
from backend.app.utils.exceptions import ProcessingError


class TestAudioService:
    """Test suite for AudioService."""
    
    @pytest.fixture
    def audio_service(self):
        """Create test audio service instance."""
        with patch.object(AudioService, '_validate_ffmpeg'):
            return AudioService()
    
    @pytest.fixture
    def mock_audio_file(self, tmp_path):
        """Create a mock audio file."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        return audio_file
    
    @pytest.fixture
    def mock_ffprobe_output(self):
        """Mock FFprobe JSON output."""
        return {
            'streams': [
                {
                    'codec_type': 'audio',
                    'codec_name': 'pcm_s16le',
                    'sample_rate': '44100',
                    'channels': 2,
                    'bit_rate': '1411200',
                    'bits_per_sample': 16,
                    'channel_layout': 'stereo'
                }
            ],
            'format': {
                'format_name': 'wav',
                'duration': '60.0',
                'size': '5292000'
            }
        }
    
    def test_audio_service_initialization(self):
        """Test audio service initialization."""
        with patch.object(AudioService, '_validate_ffmpeg') as mock_validate:
            service = AudioService('/usr/bin/ffmpeg')
            assert service.ffmpeg_path == '/usr/bin/ffmpeg'
            mock_validate.assert_called_once()
    
    @patch('subprocess.run')
    def test_validate_ffmpeg_success(self, mock_run):
        """Test successful FFmpeg validation."""
        mock_run.return_value = Mock(returncode=0)
        
        # Should not raise exception
        AudioService('/usr/bin/ffmpeg')
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_validate_ffmpeg_failure(self, mock_run):
        """Test FFmpeg validation failure."""
        mock_run.return_value = Mock(returncode=1, stderr='FFmpeg not found')
        
        with pytest.raises(ProcessingError, match="FFmpeg validation failed"):
            AudioService('/usr/bin/ffmpeg')
    
    @patch('subprocess.run')
    def test_validate_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg validation when binary not found."""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(ProcessingError, match="FFmpeg not found"):
            AudioService('/nonexistent/ffmpeg')
    
    @patch('subprocess.run')
    @patch('librosa.get_duration')
    def test_analyze_audio_file_success(self, mock_duration, mock_run, audio_service, 
                                      mock_audio_file, mock_ffprobe_output):
        """Test successful audio file analysis."""
        # Mock FFprobe output
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_ffprobe_output)
        )
        mock_duration.return_value = 60.0
        
        result = audio_service.analyze_audio_file(mock_audio_file)
        
        assert result['duration'] == 60.0
        assert result['sample_rate'] == 44100
        assert result['channels'] == 2
        assert result['codec'] == 'pcm_s16le'
        assert result['format'] == 'wav'
        assert result['file_size'] == 5292000
    
    @patch('subprocess.run')
    def test_analyze_audio_file_missing_file(self, mock_run, audio_service):
        """Test audio analysis with missing file."""
        missing_file = Path("/nonexistent/file.wav")
        
        with pytest.raises(ProcessingError, match="Audio file not found"):
            audio_service.analyze_audio_file(missing_file)
    
    @patch('subprocess.run')
    def test_analyze_audio_file_ffprobe_error(self, mock_run, audio_service, mock_audio_file):
        """Test audio analysis with FFprobe error."""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Invalid file format"
        )
        
        with pytest.raises(ProcessingError, match="FFprobe analysis failed"):
            audio_service.analyze_audio_file(mock_audio_file)
    
    @patch('subprocess.run')
    def test_analyze_audio_file_no_audio_stream(self, mock_run, audio_service, mock_audio_file):
        """Test audio analysis with no audio stream."""
        mock_output = {
            'streams': [
                {'codec_type': 'video', 'codec_name': 'h264'}
            ],
            'format': {'format_name': 'mp4', 'duration': '60.0', 'size': '1000000'}
        }
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )
        
        with pytest.raises(ProcessingError, match="No audio stream found"):
            audio_service.analyze_audio_file(mock_audio_file)
    
    def test_validate_audio_constraints_success(self, audio_service):
        """Test successful audio constraint validation."""
        metadata = {
            'duration': 60.0,
            'file_size': 1000000,
            'sample_rate': 44100,
            'codec': 'pcm_s16le'
        }
        
        # Should not raise exception
        audio_service._validate_audio_constraints(metadata)
    
    def test_validate_audio_constraints_duration_too_long(self, audio_service):
        """Test audio constraint validation with excessive duration."""
        metadata = {
            'duration': 20000.0,  # > 4 hours
            'file_size': 1000000,
            'sample_rate': 44100,
            'codec': 'pcm_s16le'
        }
        
        with pytest.raises(ProcessingError, match="duration.*exceeds maximum"):
            audio_service._validate_audio_constraints(metadata)
    
    def test_validate_audio_constraints_file_too_large(self, audio_service):
        """Test audio constraint validation with excessive file size."""
        metadata = {
            'duration': 60.0,
            'file_size': 2 * 1024 * 1024 * 1024,  # 2GB
            'sample_rate': 44100,
            'codec': 'pcm_s16le'
        }
        
        with pytest.raises(ProcessingError, match="File size.*exceeds maximum"):
            audio_service._validate_audio_constraints(metadata)
    
    def test_validate_audio_constraints_no_codec(self, audio_service):
        """Test audio constraint validation with missing codec."""
        metadata = {
            'duration': 60.0,
            'file_size': 1000000,
            'sample_rate': 44100,
            'codec': None
        }
        
        with pytest.raises(ProcessingError, match="No valid audio codec"):
            audio_service._validate_audio_constraints(metadata)
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_preprocess_for_speechkit_success(self, mock_tempfile, mock_run, 
                                            audio_service, mock_audio_file):
        """Test successful audio preprocessing."""
        # Mock temporary file
        mock_temp = Mock()
        mock_temp.name = '/tmp/processed.wav'
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        # Mock successful FFmpeg execution
        mock_run.return_value = Mock(returncode=0)
        
        # Mock output file exists and has content
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1000)
            
            result = audio_service.preprocess_for_speechkit(mock_audio_file)
            
            assert result == Path('/tmp/processed.wav')
            mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_preprocess_for_speechkit_missing_file(self, mock_run, audio_service):
        """Test preprocessing with missing input file."""
        missing_file = Path("/nonexistent/file.wav")
        
        with pytest.raises(ProcessingError, match="Input audio file not found"):
            audio_service.preprocess_for_speechkit(missing_file)
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_preprocess_for_speechkit_ffmpeg_error(self, mock_tempfile, mock_run, 
                                                 audio_service, mock_audio_file):
        """Test preprocessing with FFmpeg error."""
        mock_temp = Mock()
        mock_temp.name = '/tmp/processed.wav'
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Invalid input format"
        )
        
        with pytest.raises(ProcessingError, match="Audio preprocessing failed"):
            audio_service.preprocess_for_speechkit(mock_audio_file)
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_preprocess_for_speechkit_timeout(self, mock_tempfile, mock_run, 
                                            audio_service, mock_audio_file):
        """Test preprocessing with timeout."""
        mock_temp = Mock()
        mock_temp.name = '/tmp/processed.wav'
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('ffmpeg', 60)
        
        with pytest.raises(ProcessingError, match="Audio preprocessing timed out"):
            audio_service.preprocess_for_speechkit(mock_audio_file)
    
    @patch('subprocess.run')
    def test_convert_format_success(self, mock_run, audio_service, mock_audio_file):
        """Test successful format conversion."""
        mock_run.return_value = Mock(returncode=0)
        
        result = audio_service.convert_format(mock_audio_file, 'mp3')
        
        assert result == mock_audio_file.with_suffix('.mp3')
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_convert_format_error(self, mock_run, audio_service, mock_audio_file):
        """Test format conversion with error."""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Unsupported format"
        )
        
        with pytest.raises(ProcessingError, match="Format conversion failed"):
            audio_service.convert_format(mock_audio_file, 'unsupported')
    
    @patch('librosa.load')
    @patch('librosa.feature.rms')
    @patch('librosa.feature.spectral_centroid')
    @patch('numpy.percentile')
    def test_extract_audio_features_success(self, mock_percentile, mock_centroid, 
                                          mock_rms, mock_load, audio_service, 
                                          mock_audio_file):
        """Test successful audio feature extraction."""
        # Mock librosa functions
        mock_load.return_value = ([0.1, 0.2, 0.3], 22050)  # audio data, sample rate
        mock_rms.return_value = [[0.1, 0.2, 0.15]]
        mock_centroid.return_value = [[1000, 1200, 1100]]
        mock_percentile.return_value = 0.01
        
        # Mock other librosa functions
        with patch('librosa.feature.spectral_rolloff') as mock_rolloff, \
             patch('librosa.feature.zero_crossing_rate') as mock_zcr, \
             patch('librosa.beat.tempo') as mock_tempo, \
             patch('librosa.util.frame') as mock_frame, \
             patch('numpy.sum') as mock_sum, \
             patch('numpy.mean') as mock_mean, \
             patch('numpy.log10') as mock_log10:
            
            mock_rolloff.return_value = [[2000, 2200, 2100]]
            mock_zcr.return_value = [[0.05, 0.06, 0.055]]
            mock_tempo.return_value = [120.0]
            mock_frame.return_value = [[0.1, 0.2], [0.15, 0.25], [0.12, 0.22]]
            mock_sum.return_value = [0.02, 0.04, 0.03]
            mock_mean.return_value = 0.03
            mock_log10.return_value = 4.77
            
            features = audio_service.extract_audio_features(mock_audio_file)
            
            assert 'rms_energy' in features
            assert 'spectral_centroid' in features
            assert 'spectral_rolloff' in features
            assert 'zero_crossing_rate' in features
            assert 'tempo' in features
            assert 'snr_estimate' in features
    
    @patch('librosa.load')
    def test_extract_audio_features_error(self, mock_load, audio_service, mock_audio_file):
        """Test audio feature extraction with error."""
        mock_load.side_effect = Exception("Failed to load audio")
        
        # Should return empty dict on error, not raise exception
        features = audio_service.extract_audio_features(mock_audio_file)
        assert features == {}