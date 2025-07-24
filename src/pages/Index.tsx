import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, FileText, FileSpreadsheet, Eye } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

type TestabilityType = "Blackbox" | "Graybox" | "Whitebox";

interface Requirement {
  id: string;
  description: string;
  category?: string;
}

const Index = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [testabilityType, setTestabilityType] = useState<TestabilityType>("Blackbox");
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [parsedData, setParsedData] = useState<Requirement[] | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const fileType = file.type;
      const fileName = file.name.toLowerCase();
      
      if (fileType === "application/pdf" || fileName.endsWith(".pdf") ||
          fileType === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
          fileName.endsWith(".xlsx")) {
        setSelectedFile(file);
        setParsedData(null);
        toast({
          title: "File selected",
          description: `${file.name} is ready for upload.`,
        });
      } else {
        toast({
          title: "Invalid file type",
          description: "Please select a PDF or XLSX file.",
          variant: "destructive",
        });
      }
    }
  };

  const handlePreview = async () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please select a file first.",
        variant: "destructive",
      });
      return;
    }

    setIsPreviewLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch('http://localhost:8000/api/extract', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.success) {
        setParsedData(result.requirements);
        toast({
          title: "File processed successfully",
          description: `Found ${result.requirements.length} requirements.`,
        });
      } else {
        throw new Error(result.error || 'Failed to extract requirements');
      }
    } catch (error) {
      console.error('Error processing file:', error);
      toast({
        title: "Error processing file",
        description: error instanceof Error ? error.message : "Please try again with a different file.",
        variant: "destructive",
      });
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleProcessAndNavigate = async () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please select a file first.",
        variant: "destructive",
      });
      return;
    }

    setIsPreviewLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch('http://localhost:8000/api/extract', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.success) {
        toast({
          title: "File processed successfully",
          description: `Found ${result.requirements.length} requirements.`,
        });
        
        // Navigate directly to requirements page
        navigate("/requirements", {
          state: {
            parsedData: result.requirements,
            testabilityType,
            file: selectedFile
          }
        });
      } else {
        throw new Error(result.error || 'Failed to extract requirements');
      }
    } catch (error) {
      console.error('Error processing file:', error);
      toast({
        title: "Error processing file",
        description: error instanceof Error ? error.message : "Please try again with a different file.",
        variant: "destructive",
      });
    } finally {
      setIsPreviewLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      {/* Logo */}
      <div className="absolute top-4 left-4">
        <img 
          src="/lovable-uploads/realthinks-logo.png" 
          alt="RealThinks Logo" 
          className="h-8 w-auto"
        />
      </div>
      
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">AI Test Case Generator</h1>
          <p className="text-xl text-muted-foreground">
            Upload your requirements and generate comprehensive test cases with AI assistance
          </p>
        </div>

        <Card className="w-full max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              File Upload & Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* File Upload Section */}
            <div className="space-y-3">
              <Label htmlFor="file-upload">Select Requirements File</Label>
              <div className="flex flex-col gap-3">
                <Input
                  id="file-upload"
                  type="file"
                  accept=".pdf,.xlsx"
                  onChange={handleFileSelect}
                  ref={fileInputRef}
                  className="cursor-pointer"
                />
                {selectedFile && (
                  <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
                    {selectedFile.name.toLowerCase().endsWith(".pdf") ? (
                      <FileText className="h-4 w-4 text-red-500" />
                    ) : (
                      <FileSpreadsheet className="h-4 w-4 text-green-500" />
                    )}
                    <span className="text-sm font-medium">{selectedFile.name}</span>
                    <span className="text-xs text-muted-foreground ml-auto">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Testability Selection */}
            <div className="space-y-3">
              <Label>Testability Type</Label>
              <div className="grid grid-cols-3 gap-3">
                {(["Blackbox", "Graybox", "Whitebox"] as TestabilityType[]).map((type) => (
                  <Button
                    key={type}
                    variant={testabilityType === type ? "default" : "outline"}
                    onClick={() => setTestabilityType(type)}
                    className="w-full"
                  >
                    {type}
                  </Button>
                ))}
              </div>
            </div>

            {/* Action Button */}
            <div className="flex justify-center pt-4">
              <Button
                onClick={handleProcessAndNavigate}
                disabled={!selectedFile || isPreviewLoading}
                className="w-full flex items-center gap-2"
              >
                <FileText className="h-4 w-4" />
                {isPreviewLoading ? "Processing..." : "Process File"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Index;