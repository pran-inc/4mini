import os
import uuid
from datetime import datetime

def upload_vehicle_image(instance, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    uid = uuid.uuid4().hex
    y = datetime.now().strftime("%Y")
    m = datetime.now().strftime("%m")
    return f"vehicles/{y}/{m}/{uid}{ext}"

def upload_post_image(instance, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    uid = uuid.uuid4().hex
    y = datetime.now().strftime("%Y")
    m = datetime.now().strftime("%m")
    return f"posts/{y}/{m}/{uid}{ext}"
