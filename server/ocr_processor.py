import pytesseract
import base64
from PIL import Image
from io import BytesIO

def extract_text_from_image(base64_image):
    image_data = base64.b64decode(base64_image.split(",")[1])
    image = Image.open(BytesIO(image_data))
    text = pytesseract.image_to_string(image)
    return text