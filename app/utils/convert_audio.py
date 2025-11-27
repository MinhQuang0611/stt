from pydub import AudioSegment
import tempfile


def convert_to_wav_pcm(input_path: str) -> str:
    audio = AudioSegment.from_file(input_path)

    audio = audio.set_frame_rate(16000) \
                 .set_channels(1) \
                 .set_sample_width(2)  # 16bit PCM

    temp_wav = tempfile.mktemp(suffix=".wav")
    audio.export(temp_wav, format="wav")

    return temp_wav