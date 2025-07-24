import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ArrowLeft, Download, Edit, History } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import TestCaseModificationDialog from "@/components/TestCaseModificationDialog";
import TestCaseVersionHistory from "@/components/TestCaseVersionHistory";

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
  version?: number;
  timestamp?: string;
}

interface TestCaseVersion {
  version: number;
  timestamp: string;
  testCaseId: string;
  description: string;
  preconditions: string;
  steps: string[];
  expectedResult: string;
  postconditions: string;
  modificationReason?: string;
}

const TestCases = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedTestCases, setSelectedTestCases] = useState<Set<string>>(new Set());
  const [modificationDialogOpen, setModificationDialogOpen] = useState(false);
  const [versionHistoryOpen, setVersionHistoryOpen] = useState(false);
  const [selectedTestCaseForHistory, setSelectedTestCaseForHistory] = useState<string>("");
  const [versionHistory, setVersionHistory] = useState<Map<string, TestCaseVersion[]>>(new Map());

  useEffect(() => {
    const { testCases: passedTestCases, requirements, testabilityType, parsedData, file } = location.state || {};

    if (!passedTestCases) {
      toast({
        title: "No test cases found",
        description: "Please generate test cases first.",
        variant: "destructive",
      });
      navigate("/");
      return;
    }

    // Initialize test cases with version 1 and timestamp
    const initializedTestCases = passedTestCases.map((tc: TestCase) => ({
      ...tc,
      version: 1,
      timestamp: new Date().toISOString()
    }));

    setTestCases(initializedTestCases);

    // Initialize version history
    const initialVersionHistory = new Map();
    initializedTestCases.forEach((tc: TestCase) => {
      initialVersionHistory.set(tc.testCaseId, [{
        version: 1,
        timestamp: tc.timestamp || new Date().toISOString(),
        testCaseId: tc.testCaseId,
        description: tc.description,
        preconditions: tc.preconditions,
        steps: tc.steps,
        expectedResult: tc.expectedResult,
        postconditions: tc.postconditions,
        modificationReason: "Original test case"
      }]);
    });
    setVersionHistory(initialVersionHistory);
  }, [location.state, navigate, toast]);

  const handleBackToRequirements = () => {
    const { requirements, testabilityType, parsedData, file } = location.state || {};
    
    // Navigate back to requirements with the original data
    navigate("/requirements", {
      state: {
        parsedData: parsedData || requirements,
        testabilityType,
        file
      }
    });
  };

  const handleTestCaseSelect = (testCaseId: string, checked: boolean) => {
    const newSelected = new Set(selectedTestCases);
    if (checked) {
      newSelected.add(testCaseId);
    } else {
      newSelected.delete(testCaseId);
    }
    setSelectedTestCases(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedTestCases(new Set(testCases.map(tc => tc.id)));
    } else {
      setSelectedTestCases(new Set());
    }
  };

  const handleVersionHistory = (testCaseId: string) => {
    setSelectedTestCaseForHistory(testCaseId);
    setVersionHistoryOpen(true);
  };

  const handleVersionRestore = (version: TestCaseVersion) => {
    const updatedTestCases = testCases.map(tc => {
      if (tc.testCaseId === version.testCaseId) {
        return {
          ...tc,
          description: version.description,
          preconditions: version.preconditions,
          steps: version.steps,
          expectedResult: version.expectedResult,
          postconditions: version.postconditions,
          version: version.version,
          timestamp: new Date().toISOString()
        };
      }
      return tc;
    });

    setTestCases(updatedTestCases);
  };

  const handleDownloadAll = () => {
    const csvContent = generateCSV(testCases);
    downloadFile(csvContent, "all-test-cases.csv", "text/csv");

    toast({
      title: "Download started",
      description: "All test cases downloaded as CSV.",
    });
  };

  const handleDownloadSelected = async () => {
    const selectedTcs = testCases.filter(tc => selectedTestCases.has(tc.id));
    
    if (selectedTcs.length === 0) {
      toast({
        title: "No test cases selected",
        description: "Please select test cases to download.",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/download-selected', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          testCases: selectedTcs,
        }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "selected-test-cases.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        toast({
          title: "Download started",
          description: `${selectedTcs.length} selected test cases downloaded.`,
        });
      } else {
        throw new Error('Download failed');
      }
    } catch (error) {
      console.error('Error downloading selected test cases:', error);
      toast({
        title: "Download failed",
        description: "Please try again later.",
        variant: "destructive",
      });
    }
  };

  const handleModifySelected = () => {
    const selectedTcs = testCases.filter(tc => selectedTestCases.has(tc.id));
    
    if (selectedTcs.length === 0) {
      toast({
        title: "No test cases selected",
        description: "Please select test cases to modify.",
        variant: "destructive",
      });
      return;
    }

    setModificationDialogOpen(true);
  };

  const handleModificationComplete = (modifiedTestCases: TestCase[], isReplacement: boolean = false) => {
    const timestamp = new Date().toISOString();
    
    if (isReplacement) {
      // For split operations, replace the selected test cases with new ones
      const selectedIds = new Set(selectedTestCases);
      const remainingTestCases = testCases.filter(tc => !selectedIds.has(tc.id));
      
      // Generate new IDs for split test cases to avoid conflicts
      const newTestCases = modifiedTestCases.map((tc, index) => ({
        ...tc,
        id: `${tc.id}-split-${index}-${Date.now()}`,
        version: 1,
        timestamp
      }));
      
      setTestCases([...remainingTestCases, ...newTestCases]);
      
      // Initialize version history for new test cases
      const newVersionHistory = new Map(versionHistory);
      newTestCases.forEach(tc => {
        newVersionHistory.set(tc.testCaseId, [{
          version: 1,
          timestamp,
          testCaseId: tc.testCaseId,
          description: tc.description,
          preconditions: tc.preconditions,
          steps: tc.steps,
          expectedResult: tc.expectedResult,
          postconditions: tc.postconditions,
          modificationReason: "Split from original test case"
        }]);
      });
      setVersionHistory(newVersionHistory);
      
      toast({
        title: "Test cases updated",
        description: `Replaced ${selectedTestCases.size} test case(s) with ${newTestCases.length} new test case(s).`,
      });
    } else {
      // For regular modifications, update existing test cases
      const updatedTestCases = testCases.map(tc => {
        const modifiedTc = modifiedTestCases.find(mtc => mtc.id === tc.id);
        if (modifiedTc) {
          return {
            ...modifiedTc,
            version: (tc.version || 1) + 1,
            timestamp
          };
        }
        return tc;
      });
      
      setTestCases(updatedTestCases);
      
      // Update version history
      const newVersionHistory = new Map(versionHistory);
      modifiedTestCases.forEach(modifiedTc => {
        const originalTc = testCases.find(tc => tc.id === modifiedTc.id);
        if (originalTc) {
          const versions = newVersionHistory.get(originalTc.testCaseId) || [];
          versions.push({
            version: (originalTc.version || 1) + 1,
            timestamp,
            testCaseId: originalTc.testCaseId,
            description: modifiedTc.description,
            preconditions: modifiedTc.preconditions,
            steps: modifiedTc.steps,
            expectedResult: modifiedTc.expectedResult,
            postconditions: modifiedTc.postconditions,
            modificationReason: "Modified test case"
          });
          newVersionHistory.set(originalTc.testCaseId, versions);
        }
      });
      setVersionHistory(newVersionHistory);
    }
    
    setSelectedTestCases(new Set()); // Clear selection
  };

  const generateCSV = (data: TestCase[]) => {
    const headers = [
      "Test Case ID",
      "Requirement ID",
      "Description",
      "Preconditions",
      "Steps",
      "Expected Result",
      "Postconditions",
      "Testability Type",
    ];
    const csvRows = [headers.join(",")];

    data.forEach((testCase) => {
      const row = [
        testCase.testCaseId,
        testCase.requirementId,
        `"${testCase.description}"`,
        `"${testCase.preconditions}"`,
        `"${testCase.steps.join("; ")}"`,
        `"${testCase.expectedResult}"`,
        `"${testCase.postconditions}"`,
        testCase.testabilityType,
      ];
      csvRows.push(row.join(","));
    });

    return csvRows.join("\n");
  };

  const downloadFile = (
    content: string,
    fileName: string,
    contentType: string
  ) => {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const selectedTestCaseObjects = testCases.filter(tc => selectedTestCases.has(tc.id));

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Fixed Header */}
      <div className="flex-shrink-0 border-b bg-background p-4">
        
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                onClick={handleBackToRequirements}
                className="flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Requirements
              </Button>
              <h1 className="text-3xl font-bold">Generated Test Cases</h1>
            </div>

            <div className="flex items-center gap-2">
              <Button 
                onClick={handleDownloadAll} 
                variant="outline"
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export All
              </Button>
              <Button 
                onClick={handleDownloadSelected}
                disabled={selectedTestCases.size === 0}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export Selected ({selectedTestCases.size})
              </Button>
              <Button 
                onClick={handleModifySelected}
                disabled={selectedTestCases.size === 0}
                className="flex items-center gap-2"
              >
                <Edit className="h-4 w-4" />
                Modify Selected ({selectedTestCases.size})
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-hidden p-6">
        <div className="max-w-7xl mx-auto h-full flex flex-col">
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="flex-shrink-0">
              <CardTitle className="flex items-center justify-between">
                <span>Test Cases ({testCases.length})</span>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="select-all-testcases"
                    checked={selectedTestCases.size === testCases.length && testCases.length > 0}
                    onCheckedChange={handleSelectAll}
                  />
                  <label htmlFor="select-all-testcases" className="text-sm font-normal">
                    Select All
                  </label>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-0">
              <div className="h-full overflow-y-auto border rounded-md">
                <Table>
                  <TableHeader className="sticky top-0 bg-background z-10">
                    <TableRow>
                      <TableHead className="w-12 text-xs font-medium p-2">Select</TableHead>
                      <TableHead className="text-xs font-medium p-2">Test Case ID</TableHead>
                      <TableHead className="text-xs font-medium p-2">Requirement ID</TableHead>
                      <TableHead className="text-xs font-medium p-2">Description</TableHead>
                      <TableHead className="text-xs font-medium p-2">Preconditions</TableHead>
                      <TableHead className="text-xs font-medium p-2">Input Steps</TableHead>
                      <TableHead className="text-xs font-medium p-2">Expected Result</TableHead>
                      <TableHead className="text-xs font-medium p-2">Postconditions</TableHead>
                      <TableHead className="text-xs font-medium p-2">Type</TableHead>
                      <TableHead className="text-xs font-medium p-2">Version</TableHead>
                      <TableHead className="text-xs font-medium p-2">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {testCases.map((testCase) => (
                      <TableRow key={testCase.id}>
                        <TableCell className="p-2">
                          <Checkbox
                            checked={selectedTestCases.has(testCase.id)}
                            onCheckedChange={(checked) => 
                              handleTestCaseSelect(testCase.id, checked as boolean)
                            }
                          />
                        </TableCell>
                        <TableCell className="text-xs p-2">{testCase.testCaseId}</TableCell>
                        <TableCell className="text-xs p-2">{testCase.requirementId}</TableCell>
                        <TableCell className="max-w-[200px] p-2">
                          <div className="text-xs whitespace-pre-wrap break-words leading-relaxed" title={testCase.description}>
                            {testCase.description}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[180px] p-2">
                          <div className="text-xs whitespace-pre-wrap break-words leading-relaxed" title={testCase.preconditions}>
                            {testCase.preconditions}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[220px] p-2">
                          <div className="text-xs whitespace-pre-wrap space-y-1 leading-relaxed">
                            {testCase.steps.map((step, index) => (
                              <div key={index} className="mb-1">
                                {step}
                              </div>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[180px] p-2">
                          <div className="text-xs whitespace-pre-wrap break-words leading-relaxed" title={testCase.expectedResult}>
                            {testCase.expectedResult}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[180px] p-2">
                          <div className="text-xs whitespace-pre-wrap break-words leading-relaxed" title={testCase.postconditions}>
                            {testCase.postconditions}
                          </div>
                        </TableCell>
                        <TableCell className="text-xs p-2">{testCase.testabilityType}</TableCell>
                        <TableCell className="p-2">
                          <div className="text-xs">
                            v{testCase.version || 1}
                          </div>
                        </TableCell>
                        <TableCell className="p-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleVersionHistory(testCase.testCaseId)}
                            className="flex items-center gap-1 h-7 px-2 text-xs"
                          >
                            <History className="h-3 w-3" />
                            History
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Fixed Footer */}
      <div className="flex-shrink-0 border-t bg-background p-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <p className="text-muted-foreground">
            {selectedTestCases.size} of {testCases.length} test cases selected
          </p>
          <Button
            variant="outline"
            onClick={() => navigate("/")}
            className="flex items-center gap-2"
          >
            Restart
          </Button>
        </div>
      </div>
      <TestCaseModificationDialog
        open={modificationDialogOpen}
        onOpenChange={setModificationDialogOpen}
        selectedTestCases={selectedTestCaseObjects}
        onModificationComplete={handleModificationComplete}
      />

      <TestCaseVersionHistory
        open={versionHistoryOpen}
        onOpenChange={setVersionHistoryOpen}
        testCaseId={selectedTestCaseForHistory}
        versions={versionHistory.get(selectedTestCaseForHistory) || []}
        currentVersion={testCases.find(tc => tc.testCaseId === selectedTestCaseForHistory)?.version || 1}
        onRestore={handleVersionRestore}
      />
    </div>
  );
};

export default TestCases;
