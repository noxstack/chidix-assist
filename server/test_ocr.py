import pytesseract
from PIL import Image

# Set Tesseract path (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_path):
    text = pytesseract.image_to_string(Image.open(image_path))
    return text

# Test the function
if __name__ == "__main__":
    print(extract_text_from_image("test.png"))  # Replace with your image path