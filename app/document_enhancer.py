from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def enhance_document(
    input_path: Path,
    output_path: Path,
    scale: int = 2,
) -> None:
    """
    Enhance a low-quality document image for better readability.

    Processing:
    1. Decode original image
    2. Upscale using Lanczos interpolation
    3. Reduce visible noise
    4. Improve local contrast
    5. Apply mild sharpening
    6. Save as high-quality PNG

    This improves readability; it cannot recover details
    that are completely absent from the original image.
    """

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input image not found: {input_path}"
        )

    image = cv2.imread(
        str(input_path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            "Could not read the uploaded image."
        )

    if image.size == 0:
        raise ValueError(
            "Uploaded image is empty."
        )

    # ---------------------------------------------------------
    # 1. UPSCALE
    # ---------------------------------------------------------

    scale = max(1, min(int(scale), 4))

    if scale > 1:
        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LANCZOS4,
        )

    # ---------------------------------------------------------
    # 2. NOISE REDUCTION
    # ---------------------------------------------------------

    denoised = cv2.fastNlMeansDenoisingColored(
        image,
        None,
        h=5,
        hColor=5,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    # ---------------------------------------------------------
    # 3. LOCAL CONTRAST ENHANCEMENT
    # ---------------------------------------------------------

    lab = cv2.cvtColor(
        denoised,
        cv2.COLOR_BGR2LAB,
    )

    l_channel, a_channel, b_channel = cv2.split(
        lab
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced_l = clahe.apply(
        l_channel
    )

    enhanced_lab = cv2.merge(
        (
            enhanced_l,
            a_channel,
            b_channel,
        )
    )

    enhanced = cv2.cvtColor(
        enhanced_lab,
        cv2.COLOR_LAB2BGR,
    )

    # ---------------------------------------------------------
    # 4. MILD SHARPENING
    # ---------------------------------------------------------

    blurred = cv2.GaussianBlur(
        enhanced,
        (0, 0),
        sigmaX=1.15,
    )

    sharpened = cv2.addWeighted(
        enhanced,
        1.35,
        blurred,
        -0.35,
        0,
    )

    # Prevent invalid pixel values.
    sharpened = np.clip(
        sharpened,
        0,
        255,
    ).astype(np.uint8)

    # ---------------------------------------------------------
    # 5. SAVE HIGH-QUALITY PNG
    # ---------------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = cv2.imwrite(
        str(output_path),
        sharpened,
        [
            cv2.IMWRITE_PNG_COMPRESSION,
            1,
        ],
    )

    if not success:
        raise RuntimeError(
            "Could not save enhanced document image."
        )
