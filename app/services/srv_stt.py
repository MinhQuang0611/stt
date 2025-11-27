
import wave
import librosa
import os
import tempfile
import numpy as np
import soundfile as sf

from typing import List, Tuple
from huggingface_hub import hf_hub_download
from chunkformer import ChunkFormerModel
from typing import Union, List, Dict
from sherpa_onnx import OfflineRecognizer

from app.utils.convert_audio import convert_to_wav_pcm
class STTService:
    def __init__(self):
        self.chunkformer_model = None
        self.zipformer_model = None
    
    def load_models(self):
        """Load tất cả models"""
        
        print("="*50)
        print("Loading Chunkformer model...")
        try:
            self.chunkformer_model = ChunkFormerModel.from_pretrained(
                "khanhld/chunkformer-ctc-large-vie"
            )
            print("✓ Chunkformer model loaded successfully!")
        except Exception as e:
            print(f"✗ Failed to load Chunkformer: {e}")
        
        print("="*50)
        print("Loading Zipformer model from HuggingFace...")
        try:
            # Download các file model về local
            repo_id = "hynt/Zipformer-30M-RNNT-6000h"
            
            print("Downloading model files...")
            encoder = hf_hub_download(
                repo_id=repo_id,
                filename="encoder-epoch-20-avg-10.int8.onnx"
            )
            
            decoder = hf_hub_download(
                repo_id=repo_id,
                filename="decoder-epoch-20-avg-10.onnx"
            )
            
            joiner = hf_hub_download(
                repo_id=repo_id,
                filename="joiner-epoch-20-avg-10.int8.onnx"
            )
            
            tokens = hf_hub_download(
                repo_id=repo_id,
                filename="config.json"
            )
            
            print(f"✓ Downloaded all model files")
            print(f"Encoder: {encoder}")
            print(f"Decoder: {decoder}")
            print(f"Joiner: {joiner}")
            print(f"Tokens: {tokens}")
            
            # Khởi tạo recognizer theo cách của model.py
            self.zipformer_model = OfflineRecognizer.from_transducer(
                tokens=tokens,
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                max_active_paths=4
            )
            
            print("✓ Zipformer model loaded successfully!")
            
        except Exception as e:
            print(f"✗ Failed to load Zipformer: {e}")
            import traceback
            traceback.print_exc()
        
        print("="*50)
        print("All models loading completed!")

    @staticmethod
    def read_wave(wave_filename: str) -> Tuple[np.ndarray, int]:
        """
        Đọc file wave theo cách của sherpa-onnx
        Returns:
          - samples: 1-D array of dtype np.float32, normalized to [-1, 1]
          - sample_rate: sample rate của file
        """
        with wave.open(wave_filename) as f:
            assert f.getnchannels() == 1, f.getnchannels()
            assert f.getsampwidth() == 2, f.getsampwidth()
            num_samples = f.getnframes()
            samples = f.readframes(num_samples)
            samples_int16 = np.frombuffer(samples, dtype=np.int16)
            samples_float32 = samples_int16.astype(np.float32)
            samples_float32 = samples_float32 / 32768
            return samples_float32, f.getframerate()

    @staticmethod
    def split_audio(
        input_file: str, 
        chunk_length_sec: int = 40, 
        output_dir: str = None
    ) -> Tuple[List[str], str]:
        """Chia audio thành các chunks nhỏ"""
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        os.makedirs(output_dir, exist_ok=True)
        y, sr = librosa.load(input_file, sr=16000)
        chunk_files = []
        total_samples = len(y)
        chunk_size = chunk_length_sec * sr

        for i in range(0, total_samples, chunk_size):
            chunk = y[i:i+chunk_size]
            chunk_file = os.path.join(output_dir, f"chunk_{i//sr}.wav")
            sf.write(chunk_file, chunk, sr)
            chunk_files.append(chunk_file)
        
        return chunk_files, output_dir
    

    def transcribe_chunkformer(
        self,
        audio_path: str,
        chunk_size: int = 64,
        left_context: int = 128,
        right_context: int = 128,
        return_timestamps: bool = False
    ) -> Union[str, Dict[str, Union[str, List[Dict[str, str]]]]]:
        if self.chunkformer_model is None:
            raise RuntimeError("Chunkformer model chưa được load")
        
        response = self.chunkformer_model.endless_decode(
            audio_path=audio_path,
            chunk_size=chunk_size,
            left_context_size=left_context,
            right_context_size=right_context,
            total_batch_duration=14400,
            return_timestamps=return_timestamps
        )

        if return_timestamps:
            time_stamps = response
            transcription_text = " ".join(segment["decode"] for segment in time_stamps)
            return {
                "transcription": transcription_text,
                "time_stamps": time_stamps
            }
        else:
            return response

    def transcribe_zipformer(self, audio_path: str) -> str:
        if self.zipformer_model is None:
            raise RuntimeError("Zipformer model chưa được load")

        safe_audio_path = convert_to_wav_pcm(audio_path)

        samples, sample_rate = self.read_wave(safe_audio_path)

        stream = self.zipformer_model.create_stream()
        stream.accept_waveform(sample_rate, samples)
        self.zipformer_model.decode_stream(stream)

        result = stream.result.text

        return result


    def batch_transcribe_chunkformer(
        self,
        audio_paths: List[str],
        chunk_size: int = 64,
        left_context: int = 128,
        right_context: int = 128
    ) -> List[str]:
        """Batch transcribe với Chunkformer model"""
        if self.chunkformer_model is None:
            raise RuntimeError("Chunkformer model chưa được load")
        
        transcriptions = self.chunkformer_model.batch_decode(
            audio_paths=audio_paths,
            chunk_size=chunk_size,
            left_context_size=left_context,
            right_context_size=right_context,
            total_batch_duration=1800
        )
        return transcriptions