
import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Requirement {
  id: string;
  description: string;
  category?: string;
}

const Requirements = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [selectedRequirements, setSelectedRequirements] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [originalFile, setOriginalFile] = useState<File | null>(null);
  const [testabilityType, setTestabilityType] = useState<string>("");

  useEffect(() => {
    const { parsedData, testabilityType: passedTestabilityType, file } = location.state || {};
    
    if (!parsedData) {
      toast({
        title: "No data found",
        description: "Please upload and parse a file first.",
        variant: "destructive",
      });
      navigate("/");
      return;
    }

    setRequirements(parsedData);
    setTestabilityType(passedTestabilityType || "");
    setOriginalFile(file || null);
  }, [location.state, navigate, toast]);

  const handleRequirementSelect = (requirementId: string, checked: boolean) => {
    const newSelected = new Set(selectedRequirements);
    if (checked) {
      newSelected.add(requirementId);
    } else {
      newSelected.delete(requirementId);
    }
    setSelectedRequirements(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedRequirements(new Set(requirements.map(req => req.id)));
    } else {
      setSelectedRequirements(new Set());
    }
  };

  const handleGenerateTestCases = async () => {
    const selectedReqs = requirements.filter(req => selectedRequirements.has(req.id));
    
    if (selectedReqs.length === 0) {
      toast({
        title: "No requirements selected",
        description: "Please select at least one requirement.",
        variant: "destructive",
      });
      return;
    }

    if (!originalFile) {
      toast({
        title: "File missing",
        description: "Original file is required for test case generation.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('requirements', JSON.stringify(selectedReqs));
      formData.append('testability_type', testabilityType);
      formData.append('file', originalFile);

      const response = await fetch('http://localhost:8000/api/generate-testcases', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.success) {
        navigate("/test-cases", {
          state: {
            testCases: result.testCases,
            requirements: selectedReqs,
            testabilityType: testabilityType,
            parsedData: requirements,
            file: originalFile
          }
        });
      } else {
        throw new Error(result.error || 'Failed to generate test cases');
      }
    } catch (error) {
      console.error('Error generating test cases:', error);
      toast({
        title: "Error generating test cases",
        description: error instanceof Error ? error.message : "Please try again later.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      {/* Logo */}
      <div className="absolute top-4 left-4">
        <img 
          src="/lovable-uploads/202b2c47-de0d-4307-a5ed-97b3c7181680.png" 
          alt="Company Logo" 
          className="h-8 w-auto"
        />
      </div>
      
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => navigate("/")}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Upload
          </Button>
          <h1 className="text-3xl font-bold">Select Requirements</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Parsed Requirements ({requirements.length})</span>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="select-all"
                  checked={selectedRequirements.size === requirements.length && requirements.length > 0}
                  onCheckedChange={handleSelectAll}
                />
                <label htmlFor="select-all" className="text-sm font-normal">
                  Select All
                </label>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Select</TableHead>
                    <TableHead>ID</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Category</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requirements.map((requirement) => (
                    <TableRow key={requirement.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedRequirements.has(requirement.id)}
                          onCheckedChange={(checked) => 
                            handleRequirementSelect(requirement.id, checked as boolean)
                          }
                        />
                      </TableCell>
                      <TableCell className="font-medium">{requirement.id}</TableCell>
                      <TableCell>{requirement.description}</TableCell>
                      <TableCell>{requirement.category || "General"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-between items-center">
          <p className="text-muted-foreground">
            {selectedRequirements.size} of {requirements.length} requirements selected
          </p>
          <Button
            onClick={handleGenerateTestCases}
            disabled={loading || selectedRequirements.size === 0}
            className="flex items-center gap-2"
          >
            {loading ? "Generating..." : "Generate Test Cases"}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Requirements;
