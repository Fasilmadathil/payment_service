from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas import EventCreate
from app.services.event_service import process_event
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/")
def ingest_event(event: EventCreate, db: Session = Depends(get_db)):
    try:
        result = process_event(db, event)
        
        # If the result indicates a problem (but not an exception)
        if result.get("status") == "duplicate":
            # For duplicates, we can return 200 (idempotent success) or 409
            # Most production systems return 200 or 204 if the work is already done.
            return result
        elif result.get("status") in ["blocked", "invalid", "stale"]:
            # These are business logic errors
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")