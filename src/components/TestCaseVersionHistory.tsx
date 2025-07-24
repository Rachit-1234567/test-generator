
import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Clock, RotateCcw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

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

interface TestCaseVersionHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testCaseId: string;
  versions: TestCaseVersion[];
  currentVersion: number;
  onRestore: (version: TestCaseVersion) => void;
}

const TestCaseVersionHistory: React.FC<TestCaseVersionHistoryProps> = ({
  open,
  onOpenChange,
  testCaseId,
  versions,
  currentVersion,
  onRestore
}) => {
  const [selectedVersion, setSelectedVersion] = useState<TestCaseVersion | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const { toast } = useToast();

  const handleRestore = (version: TestCaseVersion) => {
    if (version.version === currentVersion) {
      toast({
        title: "Already current version",
        description: "This version is already the current version.",
        variant: "destructive",
      });
      return;
    }

    onRestore(version);
    toast({
      title: "Version restored",
      description: `Restored to version ${version.version}`,
    });
    onOpenChange(false);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getVersionBadgeVariant = (version: number) => {
    if (version === currentVersion) return "default";
    if (version === 1) return "outline";
    return "secondary";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Version History - {testCaseId}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {versions.map((version) => (
            <div
              key={version.version}
              className={`border rounded-lg p-4 ${
                version.version === currentVersion ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Badge variant={getVersionBadgeVariant(version.version)}>
                    Version {version.version}
                  </Badge>
                  {version.version === currentVersion && (
                    <Badge variant="outline">Current</Badge>
                  )}
                  <div className="flex items-center gap-1 text-sm text-gray-500">
                    <Clock className="h-3 w-3" />
                    {formatTimestamp(version.timestamp)}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedVersion(selectedVersion === version ? null : version)}
                  >
                    {selectedVersion === version ? "Hide Details" : "View Details"}
                  </Button>
                  {version.version !== currentVersion && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRestore(version)}
                      className="flex items-center gap-1"
                    >
                      <RotateCcw className="h-3 w-3" />
                      Restore
                    </Button>
                  )}
                </div>
              </div>

              {version.modificationReason && (
                <div className="mb-2">
                  <p className="text-sm text-gray-600">
                    <strong>Modification:</strong> {version.modificationReason}
                  </p>
                </div>
              )}

              <div className="text-sm">
                <p><strong>Description:</strong> {version.description}</p>
              </div>

              {selectedVersion === version && (
                <div className="mt-3 space-y-2 text-sm border-t pt-3">
                  <div>
                    <strong>Preconditions:</strong>
                    <p className="mt-1 text-gray-700">{version.preconditions}</p>
                  </div>
                  <div>
                    <strong>Steps:</strong>
                    <ol className="mt-1 text-gray-700 list-decimal list-inside">
                      {version.steps.map((step, index) => (
                        <li key={index}>{step}</li>
                      ))}
                    </ol>
                  </div>
                  <div>
                    <strong>Expected Result:</strong>
                    <p className="mt-1 text-gray-700">{version.expectedResult}</p>
                  </div>
                  <div>
                    <strong>Postconditions:</strong>
                    <p className="mt-1 text-gray-700">{version.postconditions}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-end">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TestCaseVersionHistory;
