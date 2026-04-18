import cloudinary
import cloudinary.uploader
import os
from typing import Optional, Dict, Any

def init_cloudinary():
    """Initialize Cloudinary with credentials from environment."""
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True
    )

def upload_certificate(file) -> Optional[Dict[str, Any]]:
    """
    Upload a medical certificate to Cloudinary.
    Support: jpg, png, pdf
    """
    try:
        init_cloudinary()
        
        # Check file type
        filename = getattr(file, 'filename', '').lower()
        if not any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.pdf']):
            print(f"[CLOUDINARY] Unsupported file type: {filename}")
            return None

        upload_result = cloudinary.uploader.upload(
            file,
            folder="healthcare_certificates",
            resource_type="auto" # Handles both images and PDFs
        )
        
        return {
            "secure_url": upload_result.get("secure_url"),
            "format": upload_result.get("format"),
            "resource_type": upload_result.get("resource_type")
        }
    except Exception as e:
        print(f"[CLOUDINARY] Upload failed: {e}")
        return None
