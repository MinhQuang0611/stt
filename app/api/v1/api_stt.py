import os
import tempfile
import shutil

from typing import List
from fastapi import APIRouter , File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.sche_stt import (
    TranscriptionRequest,
    TranscriptionResponse,
    BatchTranscriptionResponse,
    BatchTranscriptionItem,
    HealthCheckResponse
)
from app.services.srv_stt import STTService

router = APIRouter()

stt_service = STTService()

@router.on_event("startup")
async def startup_event():
    stt_service.load_models()

def save_upload_file(upload_file: UploadFile) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with open(temp_file.name, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return temp_file.name


# @router.post("/stt/omnilingual", response_model=TranscriptionResponse)
# async def transcribe_omnilingual(
#     file: UploadFile = File(...),
#     chunk_length: int = 40
# ):

#     temp_file = None
#     chunk_dir = None
    
#     try:
#         temp_file = save_upload_file(file)
#         result_text, num_chunks, chunk_dir = stt_service.transcribe_omnilingual(
#             temp_file, 
#             chunk_length
#         )
        
#         return TranscriptionResponse(
#             model="omnilingual",
#             transcription=result_text,
#             num_chunks=num_chunks,
#             status="success"
#         )
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
#     finally:
#         if temp_file and os.path.exists(temp_file):
#             os.unlink(temp_file)
#         if chunk_dir and os.path.exists(chunk_dir):
#             shutil.rmtree(chunk_dir)

@router.post("/stt/chunkformer", response_model=TranscriptionResponse)
async def transcribe_chunkformer(
    file: UploadFile = File(...),
    chunk_size: int = 64,
    left_context: int = 128,
    right_context: int = 128,
    return_timestamps: bool = False
):

    temp_file = None
    
    try:
        temp_file = save_upload_file(file)
        response = stt_service.transcribe_chunkformer(
            temp_file,
            chunk_size,
            left_context,
            right_context,
            return_timestamps
        )
        print("Transcription response:", response)
        return TranscriptionResponse(
            model="chunkformer",
            transcription=response["transcription"],
            time_stamps=response.get("time_stamps"),
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

@router.post("/stt/zipformer", response_model=TranscriptionResponse)
async def transcribe_zipformer(file: UploadFile = File(...)):

    temp_file = None
    
    try:
        temp_file = save_upload_file(file)
        transcription = stt_service.transcribe_zipformer(temp_file)
        
        return TranscriptionResponse(
            model="zipformer",
            transcription=transcription,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

@router.post("/stt/batch", response_model=BatchTranscriptionResponse)
async def transcribe_batch(
    files: List[UploadFile] = File(...),
    model_type: str = "chunkformer"
):

    if model_type != "chunkformer":
        raise HTTPException(
            status_code=400,
            detail="Batch processing chỉ hỗ trợ cho Chunkformer model"
        )
    
    temp_files = []
    
    try:
        for f in files:
            temp_file = save_upload_file(f)
            temp_files.append(temp_file)
        
        transcriptions = stt_service.batch_transcribe_chunkformer(temp_files)
        
        results = [
            BatchTranscriptionItem(
                file_name=files[i].filename,
                transcription=trans
            )
            for i, trans in enumerate(transcriptions)
        ]
        
        return BatchTranscriptionResponse(
            model="chunkformer",
            results=results,
            total_files=len(files),
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)