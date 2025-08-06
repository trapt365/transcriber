"""Audio preprocessing service for format conversion and optimization."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import librosa
import numpy as np
import json

from backend.config import get_config
from backend.app.utils.exceptions import ProcessingError

logger = logging.getLogger(__name__)
config = get_config()


class AudioService:
    """Service for audio file preprocessing and analysis."""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize audio service.
        
        Args:
            ffmpeg_path: Path to FFmpeg executable
        """
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH
        self._validate_ffmpeg()
    
    def _validate_ffmpeg(self) -> None:
        """Validate FFmpeg installation."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProcessingError(f"FFmpeg validation failed: {result.stderr}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            raise ProcessingError(f"FFmpeg not found or not working: {exc}")
    
    def analyze_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze audio file to extract metadata and characteristics.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary containing audio metadata
            
        Raises:
            ProcessingError: If analysis fails
        """
        if not file_path.exists():
            raise ProcessingError(f"Audio file not found: {file_path}")
        
        try:
            # Use FFprobe to get detailed metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ProcessingError(f"FFprobe analysis failed: {result.stderr}")
            
            metadata = json.loads(result.stdout)
            
            # Extract audio stream information
            audio_stream = None
            for stream in metadata.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise ProcessingError("No audio stream found in file")
            
            # Get format information
            format_info = metadata.get('format', {})
            
            # Use librosa for additional analysis (duration, sample rate validation)
            try:
                duration = float(format_info.get('duration', 0))
                if duration == 0:
                    # Fallback to librosa for duration
                    y, sr = librosa.load(str(file_path), sr=None, duration=1)  # Load just 1 second for quick check
                    duration = librosa.get_duration(filename=str(file_path))
            except Exception as librosa_exc:
                logger.warning(f"Librosa analysis failed: {librosa_exc}")
                duration = float(format_info.get('duration', 0))
            
            analysis_result = {
                'duration': duration,
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bit_rate': int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else None,
                'codec': audio_stream.get('codec_name'),
                'format': format_info.get('format_name'),
                'file_size': int(format_info.get('size', 0)),
                'bit_depth': audio_stream.get('bits_per_sample'),
                'channel_layout': audio_stream.get('channel_layout'),
            }
            
            # Validate constraints
            self._validate_audio_constraints(analysis_result)
            
            return analysis_result
            
        except subprocess.TimeoutExpired:
            raise ProcessingError("Audio analysis timed out")
        except json.JSONDecodeError as exc:
            raise ProcessingError(f"Failed to parse FFprobe output: {exc}")
        except Exception as exc:
            raise ProcessingError(f"Audio analysis failed: {exc}")
    
    def _validate_audio_constraints(self, metadata: Dict[str, Any]) -> None:
        """
        Validate audio file against processing constraints.
        
        Args:
            metadata: Audio metadata dictionary
            
        Raises:
            ProcessingError: If validation fails
        """
        # Check duration
        max_duration = config.MAX_AUDIO_DURATION
        if metadata['duration'] > max_duration:
            raise ProcessingError(
                f"Audio duration ({metadata['duration']:.1f}s) exceeds maximum "
                f"allowed duration ({max_duration}s)"
            )
        
        # Check file size (1GB limit for Yandex)
        max_size = 1024 * 1024 * 1024  # 1GB in bytes
        if metadata['file_size'] > max_size:
            raise ProcessingError(
                f"File size ({metadata['file_size']} bytes) exceeds maximum "
                f"allowed size ({max_size} bytes)"
            )
        
        # Validate sample rate
        valid_sample_rates = [8000, 16000, 22050, 44100, 48000]
        if metadata['sample_rate'] not in valid_sample_rates:
            logger.warning(
                f"Sample rate {metadata['sample_rate']} not optimal. "
                f"Recommended: {valid_sample_rates}"
            )
        
        # Check for audio stream
        if not metadata['codec']:
            raise ProcessingError("No valid audio codec detected")
    
    def preprocess_for_speechkit(self, input_path: Path, 
                               config_options: Optional[Dict[str, Any]] = None) -> Path:
        """
        Preprocess audio file for optimal Yandex SpeechKit processing.
        
        Args:
            input_path: Path to input audio file
            config_options: Optional preprocessing configuration
            
        Returns:
            Path to preprocessed audio file
            
        Raises:
            ProcessingError: If preprocessing fails
        """
        if not input_path.exists():
            raise ProcessingError(f"Input audio file not found: {input_path}")
        
        # Default preprocessing options
        options = {
            'sample_rate': 16000,
            'channels': 1,
            'format': 'wav',
            'codec': 'pcm_s16le',
            'normalize': True,
            'remove_silence': False,
            **(config_options or {})
        }
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(
            suffix=f'.processed.{options["format"]}',
            delete=False
        ) as temp_file:
            output_path = Path(temp_file.name)
        
        try:
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-acodec', options['codec'],
                '-ar', str(options['sample_rate']),
                '-ac', str(options['channels']),
                '-y'  # Overwrite output file
            ]
            
            # Add audio filters
            filters = []
            
            if options['normalize']:
                # Normalize audio to prevent clipping
                filters.append('volume=0.8')
            
            if options['remove_silence']:
                # Remove silence from beginning and end
                filters.append('silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB')
            
            if filters:
                cmd.extend(['-af', ','.join(filters)])
            
            cmd.append(str(output_path))
            
            logger.debug(f"Running FFmpeg preprocessing: {' '.join(cmd)}")
            
            # Execute FFmpeg with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.AUDIO_PROCESSING_TIMEOUT
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg preprocessing failed: {result.stderr}")
                raise ProcessingError(f"Audio preprocessing failed: {result.stderr}")
            
            # Verify output file was created and has content
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise ProcessingError("Preprocessing produced empty or missing output file")
            
            logger.info(f"Audio preprocessing completed: {input_path} -> {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            # Clean up output file if it exists
            if output_path.exists():
                output_path.unlink()
            raise ProcessingError("Audio preprocessing timed out")
        except Exception as exc:
            # Clean up output file if it exists
            if output_path.exists():
                output_path.unlink()
            raise ProcessingError(f"Audio preprocessing failed: {exc}")
    
    def convert_format(self, input_path: Path, output_format: str, 
                      output_path: Optional[Path] = None) -> Path:
        """
        Convert audio file to different format.
        
        Args:
            input_path: Path to input audio file
            output_format: Target format (wav, mp3, m4a, etc.)
            output_path: Optional output path
            
        Returns:
            Path to converted audio file
            
        Raises:
            ProcessingError: If conversion fails
        """
        if not input_path.exists():
            raise ProcessingError(f"Input audio file not found: {input_path}")
        
        if not output_path:
            output_path = input_path.with_suffix(f'.{output_format}')
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.AUDIO_PROCESSING_TIMEOUT
            )
            
            if result.returncode != 0:
                raise ProcessingError(f"Format conversion failed: {result.stderr}")
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise ProcessingError("Format conversion timed out")
        except Exception as exc:
            raise ProcessingError(f"Format conversion failed: {exc}")
    
    def extract_audio_features(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract advanced audio features for quality assessment.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary containing audio features
            
        Raises:
            ProcessingError: If feature extraction fails
        """
        try:
            # Load audio with librosa
            y, sr = librosa.load(str(file_path), sr=None)
            
            # Extract features
            features = {
                'rms_energy': float(librosa.feature.rms(y=y).mean()),
                'spectral_centroid': float(librosa.feature.spectral_centroid(y=y, sr=sr).mean()),
                'spectral_rolloff': float(librosa.feature.spectral_rolloff(y=y, sr=sr).mean()),
                'zero_crossing_rate': float(librosa.feature.zero_crossing_rate(y).mean()),
                'tempo': float(librosa.beat.tempo(y=y, sr=sr)[0]) if len(librosa.beat.tempo(y=y, sr=sr)) > 0 else 0.0,
            }
            
            # Calculate signal-to-noise ratio estimate
            # This is a simple estimation - silence vs. speech energy
            frame_length = 2048
            hop_length = 512
            frames = librosa.util.frame(y, frame_length=frame_length, hop_length=hop_length)
            frame_energies = np.sum(frames**2, axis=0)
            
            # Estimate noise floor (bottom 10% of frame energies)
            noise_floor = np.percentile(frame_energies, 10)
            signal_energy = np.mean(frame_energies)
            
            snr_estimate = 10 * np.log10(signal_energy / noise_floor) if noise_floor > 0 else float('inf')
            features['snr_estimate'] = float(snr_estimate)
            
            return features
            
        except Exception as exc:
            logger.warning(f"Feature extraction failed: {exc}")
            return {}


# Create default audio service instance
audio_service = AudioService()

__all__ = ['AudioService', 'audio_service']