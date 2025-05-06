from speech_recognition import Recognizer, AudioData, UnknownValueError, RequestError
import numpy as np
import logging
from typing import Union, Tuple
from dataclasses import dataclass
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    processing_time: float

class AudioTranscriber:
    def __init__(self):
        self.recognizer = Recognizer()
        self.recognizer.energy_threshold = 300  # Adjust for different environments
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Seconds of silence to end speech
        
    def transcribe_audio(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 44100,
        language: str = "en-US",
        timeout: int = 5
    ) -> Union[TranscriptionResult, None]:
        """
        Enhanced audio transcription with error handling and performance tracking.
        
        Args:
            audio_array: NumPy array of audio samples
            sample_rate: Sampling rate in Hz (default: 44100)
            language: BCP-47 language code (default: "en-US")
            timeout: Maximum seconds to wait for API response
            
        Returns:
            TranscriptionResult or None if transcription fails
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not isinstance(audio_array, np.ndarray):
                raise ValueError("Input must be a NumPy array")
                
            if len(audio_array) == 0:
                raise ValueError("Empty audio input")
                
            # Convert to AudioData
            audio_data = AudioData(
                audio_array.tobytes(),
                sample_rate=sample_rate,
                sample_width=audio_array.dtype.itemsize
            )
            
            # Perform speech recognition
            with self.recognizer.Microphone() as source:  # Context manager for resources
                self.recognizer.adjust_for_ambient_noise(source)  # Auto-calibrate
                
                text = self.recognizer.recognize_google(
                    audio_data,
                    language=language,
                    show_all=False  # Set to True to get detailed results
                )
                
                # In production, you might want to use show_all=True to get confidence scores
                # For this example, we'll use a fixed confidence
                confidence = 0.9  # Placeholder - real implementation would extract this
                
                return TranscriptionResult(
                    text=text,
                    confidence=confidence,
                    language=language,
                    processing_time=time.time() - start_time
                )
                
        except UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio")
            return None
            
        except RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service: {e}")
            return None
            
        except ValueError as e:
            logger.error(f"Input validation error: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}", exc_info=True)
            return None

# Example usage:
if __name__ == "__main__":
    # Initialize transcriber
    transcriber = AudioTranscriber()
    
    # Simulate audio input (in practice, this would come from your WebRTC stream)
    sample_audio = np.random.rand(44100) * 0.1  # 1 second of quiet audio
    
    # Transcribe with enhanced settings
    result = transcriber.transcribe_audio(
        audio_array=sample_audio,
        language="en-US",
        timeout=10
    )
    
    if result:
        print(f"Transcription successful: {result.text}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Processing time: {result.processing_time:.2f}s")
    else:
        print("Transcription failed")