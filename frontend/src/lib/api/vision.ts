/**
 * Vision OCR API client
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface VisionRequest {
  imageBase64: string;
  prompt?: string;
  model?: string;
}

export interface VisionResponse {
  success: boolean;
  content: string;
  fileType: string;
  usage?: any;
  model?: string;
}

/**
 * Process image or PDF with Mistral Vision API
 */
export async function processWithVision(request: VisionRequest): Promise<VisionResponse> {
  try {
    const response = await axios.post<VisionResponse>(`${API_URL}/vision`, {
      imageBase64: request.imageBase64,
      prompt: request.prompt || 'Extract all text and data from this image',
      model: request.model || 'pixtral-12b-2409'
    });

    return response.data;
  } catch (error: any) {
    console.error('Vision API error:', error);
    throw new Error(error.response?.data?.detail || 'Vision OCR failed');
  }
}

/**
 * Convert file to base64 data URL
 */
export async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Convert PDF to images using PDF.js
 */
export async function convertPDFToImages(file: File): Promise<string[]> {
  // @ts-ignore - PDF.js global
  const pdfjsLib = window.pdfjsLib;
  
  if (!pdfjsLib) {
    throw new Error('PDF.js not loaded. Include PDF.js script in your HTML.');
  }

  // Set up worker
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  return new Promise(async (resolve, reject) => {
    try {
      // Read file as ArrayBuffer
      const arrayBuffer = await file.arrayBuffer();
      
      // Load PDF
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      console.log(`📄 PDF loaded: ${pdf.numPages} pages`);
      
      const images: string[] = [];
      
      // Convert each page to image
      for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        const page = await pdf.getPage(pageNum);
        
        // Set scale for high quality
        const scale = 2.0;
        const viewport = page.getViewport({ scale });
        
        // Create canvas
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        if (!context) {
          throw new Error('Could not get canvas context');
        }
        
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        
        // Render page to canvas
        await page.render({
          canvasContext: context,
          viewport: viewport
        }).promise;
        
        // Convert canvas to base64 image
        const imageBase64 = canvas.toDataURL('image/png');
        images.push(imageBase64);
        
        console.log(`✅ Page ${pageNum} converted to image`);
      }
      
      resolve(images);
    } catch (error) {
      console.error('❌ PDF conversion error:', error);
      reject(error);
    }
  });
}

/**
 * Process PDF document with OCR (converts to images first)
 */
export async function processPDFWithOCR(
  file: File,
  prompt?: string,
  maxPages: number = 3
): Promise<string> {
  try {
    console.log('📄 Processing PDF with OCR...');
    
    // Convert PDF to images
    console.log('🔄 Converting PDF to images...');
    const pdfImages = await convertPDFToImages(file);
    console.log(`✅ Converted PDF to ${pdfImages.length} images`);
    
    // Process each page (or limit to maxPages)
    const pagesToProcess = Math.min(pdfImages.length, maxPages);
    let allExtractedText = '';
    
    for (let i = 0; i < pagesToProcess; i++) {
      console.log(`📄 Processing page ${i + 1}/${pagesToProcess}...`);
      
      const result = await processWithVision({
        imageBase64: pdfImages[i],
        prompt: prompt || 'Extract all text and data from this page'
      });
      
      allExtractedText += `\n\n=== PAGE ${i + 1} ===\n${result.content}`;
      console.log(`✅ Page ${i + 1} processed successfully!`);
    }
    
    console.log('✅ All pages processed successfully!');
    return allExtractedText;
    
  } catch (error) {
    console.error('❌ PDF OCR error:', error);
    throw error;
  }
}

/**
 * Ultra-Fast OCR API Functions
 */

export interface OCRExtractRequest {
  file: File;
  extractMode?: 'full' | 'structured' | 'tables';
}

export interface OCRExtractResponse {
  success: boolean;
  text: string;
  pages: string[];
  page_count: number;
  processing_time: number;
  file_name: string;
  metadata: any;
  from_cache?: boolean;
}

export interface OCRBatchResponse {
  success: boolean;
  results: any[];
  total_files: number;
  total_processing_time: number;
  successful_count: number;
  failed_count: number;
}

/**
 * Extract text from file using ultra-fast OCR
 */
export async function extractTextFromFile(
  file: File,
  extractMode: 'full' | 'structured' | 'tables' = 'full'
): Promise<OCRExtractResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post<OCRExtractResponse>(
      `${API_URL}/ocr/extract?extract_mode=${extractMode}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  } catch (error: any) {
    console.error('OCR extraction error:', error);
    throw new Error(error.response?.data?.detail || 'OCR extraction failed');
  }
}

/**
 * Extract text from multiple files concurrently (batch processing)
 */
export async function extractTextFromBatch(
  files: File[],
  extractMode: 'full' | 'structured' | 'tables' = 'full'
): Promise<OCRBatchResponse> {
  try {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await axios.post<OCRBatchResponse>(
      `${API_URL}/ocr/extract/batch?extract_mode=${extractMode}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  } catch (error: any) {
    console.error('Batch OCR error:', error);
    throw new Error(error.response?.data?.detail || 'Batch OCR extraction failed');
  }
}

/**
 * Extract text from file URL
 */
export async function extractTextFromURL(
  url: string,
  extractMode: 'full' | 'structured' | 'tables' = 'full'
): Promise<OCRExtractResponse> {
  try {
    const response = await axios.post<OCRExtractResponse>(
      `${API_URL}/ocr/extract/url`,
      {
        url,
        extract_mode: extractMode,
      }
    );

    return response.data;
  } catch (error: any) {
    console.error('URL OCR error:', error);
    throw new Error(error.response?.data?.detail || 'URL OCR extraction failed');
  }
}

/**
 * Get OCR cache statistics
 */
export async function getOCRStats() {
  try {
    const response = await axios.get(`${API_URL}/ocr/stats`);
    return response.data;
  } catch (error: any) {
    console.error('OCR stats error:', error);
    throw new Error(error.response?.data?.detail || 'Failed to get OCR stats');
  }
}

/**
 * Clear OCR cache
 */
export async function clearOCRCache() {
  try {
    const response = await axios.delete(`${API_URL}/ocr/cache/clear`);
    return response.data;
  } catch (error: any) {
    console.error('Clear cache error:', error);
    throw new Error(error.response?.data?.detail || 'Failed to clear cache');
  }
}

export default {
  processWithVision,
  fileToBase64,
  convertPDFToImages,
  processPDFWithOCR,
  // New OCR functions
  extractTextFromFile,
  extractTextFromBatch,
  extractTextFromURL,
  getOCRStats,
  clearOCRCache,
};

