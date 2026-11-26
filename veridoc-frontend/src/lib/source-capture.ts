import { documentService, DocumentOut } from "@/services/document.service";
import { featuresService } from "@/services/features.service";

type CaptureProgress = (message: string) => void;

const IMAGE_TYPES_BY_EXTENSION: Record<string, string> = {
    gif: "image/gif",
    jpeg: "image/jpeg",
    jpg: "image/jpeg",
    png: "image/png",
    webp: "image/webp",
};

const TEXT_EXTENSIONS = new Set([
    "csv",
    "htm",
    "html",
    "json",
    "log",
    "md",
    "txt",
    "xml",
    "yaml",
    "yml",
]);

const VIDEO_EXTENSIONS = new Set(["m4v", "mov", "mp4", "mpeg", "mpg"]);

function getFileExtension(fileName: string): string {
    return fileName.split(".").pop()?.toLowerCase() ?? "";
}

function fileWithType(file: File, type: string): File {
    return file.type === type
        ? file
        : new File([file], file.name, { type, lastModified: file.lastModified });
}

function wait(milliseconds: number): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export async function captureSourceFile(
    file: File,
    onProgress: CaptureProgress = () => undefined,
): Promise<DocumentOut> {
    if (file.size === 0) throw new Error("This file is empty.");

    const extension = getFileExtension(file.name);
    const fileType = file.type.toLowerCase();

    if (fileType === "application/pdf" || extension === "pdf") {
        if (file.size > 50 * 1024 * 1024) throw new Error("PDFs must be 50 MB or smaller.");
        onProgress("Uploading your PDF...");
        return documentService.upload(fileWithType(file, "application/pdf"));
    }

    const imageType = fileType.startsWith("image/")
        ? fileType
        : IMAGE_TYPES_BY_EXTENSION[extension];
    if (imageType) {
        if (file.size > 14 * 1024 * 1024) throw new Error("Images must be 14 MB or smaller.");
        onProgress("Analyzing the image...");
        const analysis = await featuresService.analyzeImage(
            fileWithType(file, imageType),
            "Describe the visible content in detail. Carefully transcribe readable text, explain important elements and their relationships, and separate direct observations from uncertain interpretations.",
        );
        if (!analysis.description.trim()) throw new Error("No readable content could be extracted from this image.");
        onProgress("Saving the image analysis...");
        return documentService.captureText(file.name, analysis.description);
    }

    const isVideo = fileType.startsWith("video/") || VIDEO_EXTENSIONS.has(extension);
    const isAudio = fileType.startsWith("audio/") || [
        "aac", "flac", "m4a", "mp3", "oga", "ogg", "opus", "wav", "webm",
    ].includes(extension);
    if (isAudio || isVideo) {
        if (file.size > 25 * 1024 * 1024) {
            throw new Error("Audio and video files must be 25 MB or smaller.");
        }
        onProgress(isVideo ? "Transcribing speech from the video..." : "Transcribing the audio...");
        const result = await featuresService.transcribeAudio(file);
        if (!result.transcript.trim()) {
            throw new Error("No speech could be transcribed from this recording.");
        }
        const content = isVideo
            ? `Transcript of ${file.name}:\n\n${result.transcript}`
            : result.transcript;
        onProgress("Saving the transcript...");
        return documentService.captureText(file.name, content);
    }

    const isText = fileType.startsWith("text/") ||
        fileType === "application/json" ||
        fileType === "application/xml" ||
        TEXT_EXTENSIONS.has(extension);
    if (isText) {
        const content = await file.text();
        if (!content.trim()) throw new Error("This text file is empty.");
        if (content.length > 200000) {
            throw new Error("Text files must contain 200,000 characters or fewer.");
        }
        onProgress("Saving your text...");
        return documentService.captureText(file.name, content);
    }

    throw new Error(
        "This file type isn’t supported yet. Use a PDF, image, audio/video recording, or text file (TXT, Markdown, CSV, JSON, HTML, XML, or YAML).",
    );
}

export async function waitForCapturedDocument(
    docId: string,
    onProgress: CaptureProgress = () => undefined,
): Promise<DocumentOut> {
    for (let attempt = 0; attempt < 180; attempt += 1) {
        await wait(2000);
        onProgress("Building your searchable source...");
        const document = await documentService.get(docId);
        if (document.status === "ready") return document;
        if (document.status === "error") {
            throw new Error(document.error_message || "We couldn’t index this source.");
        }
    }

    throw new Error("Indexing is taking longer than expected. Check My Documents for its status.");
}
