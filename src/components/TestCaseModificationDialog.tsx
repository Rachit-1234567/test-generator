
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Info } from "lucide-react";
import FileAttachment from "./FileAttachment";

interface TestCase {
  id: string;
  testCaseId: string;
  description: string;
  preconditions: string;
  steps: string[];
  expectedResult: string;
  testabilityType: string;
  postconditions: string;
  requirementId: string;
}

interface AttachedFile {
  id: string;
  file: File;
  type: 'image' | 'pdf' | 'text' | 'document';
  preview?: string;
}

interface TestCaseModificationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedTestCases: TestCase[];
  onModificationComplete: (modifiedTestCases: TestCase[], isReplacement?: boolean) => void;
}

const TestCaseModificationDialog = ({
  open,
  onOpenChange,
  selectedTestCases,
  onModificationComplete,
}: TestCaseModificationDialogProps) => {
  const [modificationInput, setModificationInput] = useState("");
  const [attachments, setAttachments] = useState<AttachedFile[]>([]);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // Detect if the user wants to split test cases
  const isSplitRequest = modificationInput.toLowerCase().includes('split') && 
    (modificationInput.toLowerCase().includes('2') || 
     modificationInput.toLowerCase().includes('3') || 
     modificationInput.toLowerCase().includes('4') ||   
     modificationInput.toLowerCase().includes('5') || 
     modificationInput.toLowerCase().includes('two') || 
     modificationInput.toLowerCase().includes('three') || 
     modificationInput.toLowerCase().includes('four') || 
     modificationInput.toLowerCase().includes('five') ||
     modificationInput.toLowerCase().includes('multiple'));

  const handleModify = async () => {
    if (!modificationInput.trim()) {
      toast({
        title: "Input required",
        description: "Please describe the modifications you want to make.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('testCases', JSON.stringify(selectedTestCases));
      formData.append('modificationInstruction', modificationInput);
      formData.append('isSplitRequest', isSplitRequest.toString());

      // Add attachments to FormData
      attachments.forEach((attachment, index) => {
        formData.append(`attachments`, attachment.file);
      });

      const response = await fetch('http://localhost:8000/api/modify-testcases', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.success) {
        // If it's a split request, we're replacing the original test cases
        onModificationComplete(result.modifiedTestCases, isSplitRequest);
        toast({
          title: isSplitRequest ? "Test cases split successfully" : "Test cases modified",
          description: isSplitRequest 
            ? `Split into ${result.modifiedTestCases.length} test cases.`
            : `Successfully modified ${selectedTestCases.length} test case(s).`,
        });
        onOpenChange(false);
        setModificationInput("");
        setAttachments([]);
      } else {
        throw new Error(result.error || 'Failed to modify test cases');
      }
    } catch (error) {
      console.error('Error modifying test cases:', error);
      toast({
        title: "Error modifying test cases",
        description: error instanceof Error ? error.message : "Please try again later.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setModificationInput("");
    setAttachments([]);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Modify Selected Test Cases ({selectedTestCases.length})</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {isSplitRequest && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <Info className="h-4 w-4 text-blue-600" />
              <div className="text-sm text-blue-800">
                <Badge variant="secondary" className="mr-2">Split Mode</Badge>
                This will split the selected test cases into multiple new test cases.
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium mb-2 block">
              Describe the modifications you want to make:
            </label>
            <Textarea
              placeholder="e.g., 'make input values more specific', 'add safety-related preconditions', 'split this test case into 3 separate test cases'"
              value={modificationInput}
              onChange={(e) => setModificationInput(e.target.value)}
              rows={4}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">
              Attach supporting files (optional):
            </label>
            <FileAttachment
              attachments={attachments}
              onAttachmentsChange={setAttachments}
              disabled={loading}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleModify}
              disabled={loading || !modificationInput.trim()}
            >
              {loading ? "Processing..." : isSplitRequest ? "Split Test Cases" : "Apply Modifications"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TestCaseModificationDialog;
