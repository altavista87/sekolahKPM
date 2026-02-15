"""Image processing utilities including HEIC conversion."""
import logging
from pathlib import Path
from typing import Optional
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False
    logging.warning("pillow-heif not installed. HEIC support disabled.")

logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
if HEIC_SUPPORT:
    SUPPORTED_FORMATS.update(['.heic', '.heif'])

SUPPORTED_MIME_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 
    'image/bmp', 'image/tiff'
]
if HEIC_SUPPORT:
    SUPPORTED_MIME_TYPES.extend(['image/heic', 'image/heif'])


def convert_to_jpeg(image_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert any supported image format to JPEG.
    
    Args:
        image_path: Path to input image
        output_path: Optional path for output (defaults to input + .jpg)
        
    Returns:
        Path to converted JPEG file
        
    Raises:
        ValueError: If format not supported
        RuntimeError: If conversion fails
    """
    input_path = Path(image_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Determine output path
    if output_path is None:
        output_path = str(input_path.with_suffix('.jpg'))
    
    # Check if already JPEG
    if input_path.suffix.lower() in ['.jpg', '.jpeg']:
        logger.info(f"Image already JPEG: {image_path}")
        return image_path
    
    # Validate format support
    if input_path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported image format: {input_path.suffix}. "
            f"Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    try:
        # Open and convert image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, P modes)
            if img.mode in ('RGBA', 'P', 'LA', 'L'):
                # For HEIC, always convert to RGB
                rgb_img = img.convert('RGB')
            else:
                rgb_img = img
            
            # Save as JPEG with quality 95
            rgb_img.save(output_path, 'JPEG', quality=95, optimize=True)
        
        logger.info(f"Converted {image_path} -> {output_path}")
        return output_path
        
    except Exception as e:
        raise RuntimeError(f"Failed to convert image: {e}")


def validate_image(image_path: str) -> dict:
    """
    Validate image file and return metadata.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dict with: valid, format, size, width, height, error
    """
    result = {
        'valid': False,
        'format': None,
        'size_bytes': 0,
        'width': 0,
        'height': 0,
        'error': None
    }
    
    try:
        path = Path(image_path)
        
        if not path.exists():
            result['error'] = "File not found"
            return result
        
        result['size_bytes'] = path.stat().st_size
        
        # Check format support
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            result['error'] = f"Unsupported format: {path.suffix}"
            return result
        
        # Try to open and validate
        with Image.open(image_path) as img:
            result['format'] = img.format
            result['width'] = img.width
            result['height'] = img.height
            result['valid'] = True
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


def get_supported_formats() -> list:
    """Return list of supported image formats."""
    formats = ['JPEG', 'PNG', 'GIF', 'WebP', 'BMP', 'TIFF']
    if HEIC_SUPPORT:
        formats.extend(['HEIC', 'HEIF'])
    return formats


def check_heic_support() -> bool:
    """Check if HEIC support is available."""
    return HEIC_SUPPORT
