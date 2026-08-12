export type ImageStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Image {
  id: string;
  filename: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  uploaded_at: string;
  taken_at: string | null;
  camera: string | null;
  lens: string | null;
  gps: string | null;
  status: ImageStatus;
  url: string;
  thumbnail_url: string | null;
}

export interface ImageList {
  items: Image[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadsPerDay {
  date: string;
  count: number;
}

export interface ImageStats {
  count: number;
  storage_bytes: number;
  by_status: Record<ImageStatus, number>;
  by_mime_type: Record<string, number>;
  uploads_per_day: UploadsPerDay[];
}

export interface DetectedObject {
  id: string;
  class_name: string;
  confidence: number;
  bounding_box: number[];
}

export interface OCRResult {
  id: string;
  text: string;
  language: string | null;
  confidence: number;
}

export interface Caption {
  id: string;
  text: string;
  model: string;
}

export interface ImageDetail extends Image {
  dominant_colors: string[] | null;
  objects: DetectedObject[];
  ocr: OCRResult[];
  caption: Caption | null;
}
