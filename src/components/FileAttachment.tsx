
import React, { useState, useCallback } from 'react';
import { Upload, X, File, Image as ImageIcon } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

interface AttachedFile {
  id: string;
  file: File;
  type: 'image' | 'pdf' | 'text' | 'document';
  preview?: string;
}

interface FileAttachmentProps {
  attachments: AttachedFile[];
  onAttachmentsChange: (attachments: AttachedFile[]) => void;
  disabled?: boolean;
}

const FileAttachment: React.FC<FileAttachmentProps> = ({
  attachments,
  onAttachmentsChange,
  disabled = false
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const { toast } = useToast();

  const acceptedTypes = [
    'application/pdf',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg',
    'image/webp'
  ];

  const getFileType = (file: File): AttachedFile['type'] => {
    if (file.type.startsWith('image/')) return 'image';
    if (file.type === 'application/pdf') return 'pdf';
    if (file.type === 'text/plain') return 'text';
    return 'document';
  };

  const generatePreview = (file: File): Promise<string | undefined> => {
    return new Promise((resolve) => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.readAsDataURL(file);
      } else {
        resolve(undefined);
      }
    });
  };

  const handleFiles = useCallback(async (files: FileList) => {
    const newAttachments: AttachedFile[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      if (!acceptedTypes.includes(file.type)) {
        toast({
          title: "Unsupported file type",
          description: `${file.name} is not supported. Please use PDF, TXT, DOCX, PNG, JPG, or WEBP files.`,
          variant: "destructive",
        });
        continue;
      }

      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast({
          title: "File too large",
          description: `${file.name} is too large. Please use files smaller than 10MB.`,
          variant: "destructive",
        });
        continue;
      }

      const preview = await generatePreview(file);
      
      newAttachments.push({
        id: `${Date.now()}-${i}`,
        file,
        type: getFileType(file),
        preview
      });
    }

    onAttachmentsChange([...attachments, ...newAttachments]);
  }, [attachments, onAttachmentsChange, toast]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    
    const files = e.dataTransfer.files;
    handleFiles(files);
  }, [disabled, handleFiles]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      handleFiles(files);
    }
  }, [handleFiles]);

  const removeAttachment = useCallback((id: string) => {
    onAttachmentsChange(attachments.filter(att => att.id !== id));
  }, [attachments, onAttachmentsChange]);

  const getFileIcon = (type: AttachedFile['type']) => {
    switch (type) {
      case 'image':
        return <ImageIcon className="h-4 w-4" />;
      case 'pdf':
        return <File className="h-4 w-4 text-red-500" />;
      case 'text':
        return <File className="h-4 w-4 text-blue-500" />;
      case 'document':
        return <File className="h-4 w-4 text-green-500" />;
      default:
        return <File className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Drag and Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
          isDragOver
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          multiple
          accept=".pdf,.txt,.docx,.png,.jpg,.jpeg,.webp"
          onChange={handleFileSelect}
          disabled={disabled}
          className="hidden"
          id="file-input"
        />
        <label htmlFor="file-input" className={`cursor-pointer ${disabled ? 'cursor-not-allowed' : ''}`}>
          <Upload className="h-8 w-8 mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600">
            Drag and drop files here or click to select
          </p>
          <p className="text-xs text-gray-500 mt-1">
            PDF, TXT, DOCX, PNG, JPG, WEBP (max 10MB)
          </p>
        </label>
      </div>

      {/* Attached Files Preview */}
      {attachments.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Attached Files:</h4>
          <div className="space-y-2">
            {attachments.map((attachment) => (
              <div key={attachment.id} className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg">
                {attachment.preview ? (
                  <img
                    src={attachment.preview}
                    alt={attachment.file.name}
                    className="h-10 w-10 object-cover rounded"
                  />
                ) : (
                  <div className="h-10 w-10 flex items-center justify-center bg-gray-200 rounded">
                    {getFileIcon(attachment.type)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{attachment.file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(attachment.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeAttachment(attachment.id)}
                  disabled={disabled}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileAttachment;
