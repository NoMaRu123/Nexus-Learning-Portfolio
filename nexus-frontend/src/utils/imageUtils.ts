/**
 * Client-side image validation, cropping, and compression utilities.
 *
 * Used by the Profile page to validate uploaded files, crop them to a
 * 1:1 aspect ratio via react-easy-crop, and compress/resize to a max
 * of 512×512 pixels before uploading to the backend.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Pixel-based crop area returned by react-easy-crop. */
export interface Area {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Result of client-side file validation. */
export interface ValidationResult {
  valid: boolean;
  error?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const MAX_OUTPUT_DIMENSION = 512;

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Validate an image file for acceptable MIME type and size.
 *
 * Accepts JPEG, PNG, and WebP files up to 5 MB.
 */
export function validateImageFile(file: File): ValidationResult {
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    return {
      valid: false,
      error: "Invalid file type. Please upload a JPEG, PNG, or WebP image.",
    };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: "File is too large. Maximum size is 5 MB.",
    };
  }

  return { valid: true };
}

// ---------------------------------------------------------------------------
// Image loading
// ---------------------------------------------------------------------------

/**
 * Load an image from a data URL or object URL and return the
 * HTMLImageElement once it has finished loading.
 */
export function createImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", (error) => reject(error));
    image.setAttribute("crossOrigin", "anonymous");
    image.src = url;
  });
}

// ---------------------------------------------------------------------------
// Crop + resize
// ---------------------------------------------------------------------------

/**
 * Crop the source image to the given pixel area and resize the result
 * to a maximum of 512×512 pixels. Returns a Blob in JPEG format.
 *
 * Uses an off-screen canvas to perform the crop and resize entirely
 * on the client side, avoiding unnecessary bandwidth to the backend.
 */
export async function getCroppedImg(
  imageSrc: string,
  pixelCrop: Area,
): Promise<Blob> {
  const image = await createImage(imageSrc);

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Could not get canvas 2D context");
  }

  // Determine output size — scale down if the crop exceeds 512px.
  const scale = Math.min(
    1,
    MAX_OUTPUT_DIMENSION / pixelCrop.width,
    MAX_OUTPUT_DIMENSION / pixelCrop.height,
  );

  const outputWidth = Math.round(pixelCrop.width * scale);
  const outputHeight = Math.round(pixelCrop.height * scale);

  canvas.width = outputWidth;
  canvas.height = outputHeight;

  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    outputWidth,
    outputHeight,
  );

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error("Canvas toBlob returned null"));
        }
      },
      "image/jpeg",
      0.9,
    );
  });
}
