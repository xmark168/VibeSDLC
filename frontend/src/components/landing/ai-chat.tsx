import { useEffect, useRef, useCallback } from "react";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
    Image,
    FileUp,
    Figma,
    Monitor,
    CircleUserRound,
    ArrowUp,
    Paperclip,
    Plus,
    X,
    FileText,
    Image as ImageIcon,
    FileCode,
    FileArchive,
    File,
    Video,
    FileSpreadsheet,
    FileType
} from "lucide-react";

interface UseAutoResizeTextareaProps {
    minHeight: number;
    maxHeight?: number;
}

function useAutoResizeTextarea({
    minHeight,
    maxHeight,
}: UseAutoResizeTextareaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const adjustHeight = useCallback(
        (reset?: boolean) => {
            const textarea = textareaRef.current;
            if (!textarea) return;

            if (reset) {
                textarea.style.height = `${minHeight}px`;
                return;
            }

            // Temporarily shrink to get the right scrollHeight
            textarea.style.height = `${minHeight}px`;

            // Calculate new height
            const newHeight = Math.max(
                minHeight,
                Math.min(
                    textarea.scrollHeight,
                    maxHeight ?? Number.POSITIVE_INFINITY
                )
            );

            textarea.style.height = `${newHeight}px`;
        },
        [minHeight, maxHeight]
    );

    useEffect(() => {
        // Set initial height
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = `${minHeight}px`;
        }
    }, [minHeight]);

    // Adjust height on window resize
    useEffect(() => {
        const handleResize = () => adjustHeight();
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, [adjustHeight]);

    return { textareaRef, adjustHeight };
}

interface UploadedFile {
    id: string;
    name: string;
    type: string;
}

export default function AIChat() {
    const [value, setValue] = useState("");
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const filesContainerRef = useRef<HTMLDivElement>(null);
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 60,
        maxHeight: 200,
    });
    useEffect(() => {
        const filesContainer = filesContainerRef.current;
        if (!filesContainer) return;

        const handleWheel = (e: WheelEvent) => {
            if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
                // Nếu đang scroll ngang thì không làm gì
                return;
            }

            // Scroll ngang khi scroll dọc
            e.preventDefault();
            filesContainer.scrollLeft += e.deltaY;
        };

        filesContainer.addEventListener('wheel', handleWheel, { passive: false });

        return () => {
            filesContainer.removeEventListener('wheel', handleWheel);
        };
    }, []);
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (value.trim()) {
                setValue("");
                adjustHeight(true);
            }
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files) {
            const newFiles: UploadedFile[] = Array.from(files).map((file) => ({
                id: Math.random().toString(36).substr(2, 9),
                name: file.name,
                type: file.type,
            }));
            // Giới hạn tối đa 10 file
            setUploadedFiles((prev) => [...prev, ...newFiles].slice(0, 10));
        }
        // Reset input
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const removeFile = (id: string) => {
        setUploadedFiles((prev) => prev.filter((file) => file.id !== id));
    };

    const getFileIcon = (fileName: string, fileType: string) => {
        const ext = fileName.split(".").pop()?.toLowerCase();

        // Check by file type first
        if (fileType.startsWith('image/')) {
            return <ImageIcon className="w-4 h-4 text-blue-400" />;
        }
        if (fileType.startsWith('video/')) {
            return <Video className="w-4 h-4 text-purple-400" />;
        }
        if (fileType.startsWith('audio/')) {
            return <ArrowUp className="w-4 h-4 text-green-400" />;
        }

        // Check by extension
        switch (ext) {
            case 'pdf':
                return <FileType className="w-4 h-4 text-red-400" />;
            case 'doc':
            case 'docx':
                return <FileText className="w-4 h-4 text-blue-500" />;
            case 'xls':
            case 'xlsx':
            case 'csv':
                return <FileSpreadsheet className="w-4 h-4 text-green-500" />;
            case 'js':
            case 'jsx':
            case 'ts':
            case 'tsx':
            case 'html':
            case 'css':
            case 'py':
            case 'java':
            case 'cpp':
            case 'c':
                return <FileCode className="w-4 h-4 text-yellow-400" />;
            case 'zip':
            case 'rar':
            case '7z':
            case 'tar':
            case 'gz':
                return <FileArchive className="w-4 h-4 text-orange-400" />;
            case 'bpmn':
                return <FileText className="w-4 h-4 text-purple-500" />;
            default:
                return <File className="w-4 h-4 text-gray-400" />;
        }
    };

    const truncateFileName = (fileName: string, maxLength: number = 20) => {
        if (fileName.length <= maxLength) return fileName;
        const extension = fileName.split('.').pop();
        const nameWithoutExt = fileName.slice(0, -(extension?.length || 0) - 1);
        const truncatedName = nameWithoutExt.slice(0, maxLength - extension!.length - 3);
        return `${truncatedName}...${extension}`;
    };

    return (
        <div className="flex flex-col items-center w-full max-w-4xl mx-auto p-4 space-y-8">
            <h1 className="text-4xl font-bold text-black dark:text-white">
                What can I help you ship?
            </h1>

            <div className="w-full">
                <div className="relative bg-neutral-900 rounded-xl border border-neutral-800">
                    {/* Uploaded Files Display - Scroll ngang */}
                    {uploadedFiles.length > 0 && (
                        <div className="px-4 pt-3 pb-2 border-b border-neutral-800">
                            <div
                                ref={filesContainerRef}
                                className="flex gap-2 overflow-x-auto scrollbar-thin scrollbar-thumb-neutral-700 scrollbar-track-neutral-800 scrollbar-h-1"
                            >
                                {uploadedFiles.map((file) => (
                                    <div
                                        key={file.id}
                                        className="flex items-center gap-2 px-3 py-2 bg-neutral-800 rounded-lg group hover:bg-neutral-700 transition-colors flex-shrink-0 min-w-0 max-w-[200px]"
                                        style={{
                                            scrollBehavior: 'smooth',
                                            WebkitOverflowScrolling: 'touch'
                                        }}
                                    >
                                        <div className="flex items-center gap-2 flex-1 min-w-0">
                                            <div className="w-8 h-8 bg-neutral-700 rounded flex items-center justify-center flex-shrink-0">
                                                {getFileIcon(file.name, file.type)}
                                            </div>
                                            <div className="flex flex-col min-w-0 flex-1">
                                                <span
                                                    className="text-xs text-white font-medium truncate"
                                                    title={file.name}
                                                >
                                                    {truncateFileName(file.name)}
                                                </span>
                                                <span className="text-[10px] text-neutral-500">
                                                    {file.type.split('/')[1]?.toUpperCase() ||
                                                        file.name.split('.').pop()?.toUpperCase() ||
                                                        'FILE'}
                                                </span>
                                            </div>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => removeFile(file.id)}
                                            className="opacity-70 group-hover:opacity-100 p-1 hover:bg-neutral-600 rounded transition-all flex-shrink-0"
                                        >
                                            <X className="w-3 h-3 text-neutral-400 hover:text-white" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Textarea */}
                    <div className="overflow-y-auto">
                        <Textarea
                            ref={textareaRef}
                            value={value}
                            onChange={(e) => {
                                setValue(e.target.value);
                                adjustHeight();
                            }}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask VibeSDLC a question..."
                            className={cn(
                                "w-full px-4 py-3",
                                "resize-none",
                                "bg-transparent",
                                "border-none",
                                "text-sm",
                                "focus:outline-none",
                                "focus-visible:ring-0 focus-visible:ring-offset-0",
                                "placeholder:text-neutral-500 placeholder:text-sm",
                                "min-h-[60px]"
                            )}
                            style={{
                                overflow: "hidden",
                            }}
                        />
                    </div>

                    {/* Bottom Controls */}
                    <div className="flex items-center justify-between p-3">
                        <div className="flex items-center gap-2">
                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                onChange={handleFileSelect}
                                className="hidden"
                            />
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                className="group p-2 hover:bg-neutral-800 rounded-lg transition-colors flex items-center gap-1"
                            >
                                <Paperclip className="w-4 h-4 text-white" />
                                <span className="text-xs text-zinc-400 hidden group-hover:inline transition-opacity">
                                    Attach
                                </span>
                            </button>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                className="px-2 py-1 rounded-lg text-sm text-zinc-400 transition-colors border border-dashed border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800 flex items-center justify-between gap-1"
                            >
                                <Plus className="w-4 h-4" />
                                Project
                            </button>
                            <button
                                type="button"
                                className={cn(
                                    "px-1.5 py-1.5 rounded-lg text-sm transition-colors border border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800 flex items-center justify-between gap-1",
                                    value.trim()
                                        ? "bg-white text-black"
                                        : "text-zinc-400"
                                )}
                            >
                                <ArrowUp
                                    className={cn(
                                        "w-4 h-4",
                                        value.trim()
                                            ? "text-black"
                                            : "text-zinc-400"
                                    )}
                                />
                                <span className="sr-only">Send</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-center gap-3 mt-4">
                    <ActionButton
                        icon={<Image className="w-4 h-4" />}
                        label="Clone a Screenshot"
                    />
                    <ActionButton
                        icon={<Figma className="w-4 h-4" />}
                        label="Import from Figma"
                    />
                    <ActionButton
                        icon={<FileUp className="w-4 h-4" />}
                        label="Upload a Project"
                    />
                    <ActionButton
                        icon={<Monitor className="w-4 h-4" />}
                        label="Landing Page"
                    />
                    <ActionButton
                        icon={<CircleUserRound className="w-4 h-4" />}
                        label="Sign Up Form"
                    />
                </div>
            </div>

            {/* Custom scrollbar styles */}
            <style>{`
                .scrollbar-thin::-webkit-scrollbar {
                    height: 4px;
                }
                .scrollbar-thin::-webkit-scrollbar-track {
                    background: #404040;
                    border-radius: 2px;
                }
                .scrollbar-thin::-webkit-scrollbar-thumb {
                    background: #525252;
                    border-radius: 2px;
                }
                .scrollbar-thin::-webkit-scrollbar-thumb:hover {
                    background: #666;
                }
            `}</style>
        </div>
    );
}

interface ActionButtonProps {
    icon: React.ReactNode;
    label: string;
}

function ActionButton({ icon, label }: ActionButtonProps) {
    return (
        <button
            type="button"
            className="flex items-center gap-2 px-4 py-2 bg-neutral-900 hover:bg-neutral-800 rounded-full border border-neutral-800 text-neutral-400 hover:text-white transition-colors"
        >
            {icon}
            <span className="text-xs">{label}</span>
        </button>
    );
}