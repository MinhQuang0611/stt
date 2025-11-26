from pydantic import BaseModel, Field
from typing import List, Optional

class TranscriptionRequest(BaseModel):
    chunk_length: Optional[int] = Field(default=40, description="Độ dài mỗi chunk (giây)")
    chunk_size: Optional[int] = Field(default=64, description="Chunk size cho Chunkformer")
    left_context: Optional[int] = Field(default=128, description="Left context size")
    right_context: Optional[int] = Field(default=128, description="Right context size")
    return_timestamps: Optional[bool] = Field(default=False, description="Trả về timestamps")

class TranscriptionResponse(BaseModel):
    model: str
    transcription: str
    status: str
    num_chunks: Optional[int] = None
    time_stamps: Optional[List[dict]] = None

class BatchTranscriptionItem(BaseModel):
    file_name: str
    transcription: str

class BatchTranscriptionResponse(BaseModel):
    model: str
    results: List[BatchTranscriptionItem]
    total_files: int
    status: str

class HealthCheckResponse(BaseModel):
    status: str
    available_models: List[str]
    message: str