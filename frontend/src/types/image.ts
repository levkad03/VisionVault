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
