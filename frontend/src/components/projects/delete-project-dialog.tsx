import { useState, useEffect } from "react";
import { AlertTriangle, Loader2, Users, FileText, MessageSquare, Folder, Bot, Package } from "lucide-react";
import { OpenAPI } from "@/client";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DeletionPreview {
    project_id: string;
    project_name: string;
    project_code: string;
    counts: {
        agents: number;
        stories: number;
        epics: number;
        messages: number;
        executions: number;
        artifacts: number;
    };
    has_workspace: boolean;
    workspace_path: string | null;
}

interface DeleteProjectDialogProps {
    projectId: string;
    projectName: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: () => void;
}

export function DeleteProjectDialog({
    projectId,
    projectName,
    open,
    onOpenChange,
    onConfirm,
}: DeleteProjectDialogProps) {
    const [preview, setPreview] = useState<DeletionPreview | null>(null);
    const [loading, setLoading] = useState(false);
    const [confirmText, setConfirmText] = useState("");
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (open && projectId) {
            fetchPreview();
        } else {
            setPreview(null);
            setConfirmText("");
        }
    }, [open, projectId]);

    const fetchPreview = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem("access_token");
            const response = await fetch(`${OpenAPI.BASE}/api/v1/projects/${projectId}/deletion-preview`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (response.ok) {
                const data = await response.json();
                setPreview(data);
            }
        } catch (error) {
            console.error("Failed to fetch deletion preview:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleConfirm = async () => {
        setDeleting(true);
        try {
            await onConfirm();
        } finally {
            setDeleting(false);
            onOpenChange(false);
        }
    };

    const totalItems = preview
        ? preview.counts.agents +
          preview.counts.stories +
          preview.counts.epics +
          preview.counts.messages +
          preview.counts.executions +
          preview.counts.artifacts
        : 0;

    const canDelete = confirmText.toLowerCase() === projectName.toLowerCase();

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent className="max-w-md" onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                    <AlertDialogTitle className="flex items-center gap-2 text-destructive">
                        <AlertTriangle className="h-5 w-5" />
                        Delete Project
                    </AlertDialogTitle>
                    <AlertDialogDescription asChild>
                        <div className="space-y-4">
                            <p>
                                Are you sure you want to delete{" "}
                                <span className="font-semibold text-foreground">"{projectName}"</span>?
                                This action cannot be undone.
                            </p>

                            {loading ? (
                                <div className="flex items-center justify-center py-4">
                                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : preview ? (
                                <div className="rounded-lg border bg-muted/50 p-4 space-y-3">
                                    <p className="text-sm font-medium text-foreground">
                                        The following data will be permanently deleted:
                                    </p>
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        <div className="flex items-center gap-2">
                                            <Bot className="h-4 w-4 text-blue-500" />
                                            <span>{preview.counts.agents} agents</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <FileText className="h-4 w-4 text-green-500" />
                                            <span>{preview.counts.stories} stories</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Package className="h-4 w-4 text-purple-500" />
                                            <span>{preview.counts.epics} epics</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <MessageSquare className="h-4 w-4 text-orange-500" />
                                            <span>{preview.counts.messages} messages</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Users className="h-4 w-4 text-cyan-500" />
                                            <span>{preview.counts.executions} executions</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Folder className="h-4 w-4 text-yellow-500" />
                                            <span>{preview.counts.artifacts} artifacts</span>
                                        </div>
                                    </div>
                                    {preview.has_workspace && (
                                        <p className="text-xs text-muted-foreground border-t pt-2">
                                            + Project workspace files will be deleted
                                        </p>
                                    )}
                                </div>
                            ) : null}

                            <div className="space-y-2">
                                <Label htmlFor="confirm-name" className="text-sm">
                                    Type <span className="font-semibold text-foreground">"{projectName}"</span> to confirm:
                                </Label>
                                <Input
                                    id="confirm-name"
                                    value={confirmText}
                                    onChange={(e) => setConfirmText(e.target.value)}
                                    onClick={(e) => e.stopPropagation()}
                                    onMouseDown={(e) => e.stopPropagation()}
                                    placeholder="Enter project name"
                                    className="bg-background"
                                />
                            </div>
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleConfirm}
                        disabled={!canDelete || deleting}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        {deleting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Deleting...
                            </>
                        ) : (
                            `Delete ${totalItems > 0 ? `(${totalItems} items)` : ""}`
                        )}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
