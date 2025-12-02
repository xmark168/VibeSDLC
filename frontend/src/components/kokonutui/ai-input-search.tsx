import { ArrowUp } from "lucide-react";
import { useState, forwardRef, useImperativeHandle, type ReactNode } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";

export interface AIInputSearchProps {
    value?: string;
    onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
    onSubmit?: () => void;
    placeholder?: string;
    disabled?: boolean;
    leftActions?: ReactNode;
    className?: string;
}

export interface AIInputSearchRef {
    focus: () => void;
    textareaRef: React.RefObject<HTMLTextAreaElement>;
    adjustHeight: (reset?: boolean) => void;
}

const AIInputSearch = forwardRef<AIInputSearchRef, AIInputSearchProps>(
    (
        {
            value: controlledValue,
            onChange,
            onKeyDown,
            onSubmit,
            placeholder = "Type a message...",
            disabled = false,
            leftActions,
            className,
        },
        ref
    ) => {
        const [internalValue, setInternalValue] = useState("");
        const { textareaRef, adjustHeight } = useAutoResizeTextarea({
            minHeight: 52,
            maxHeight: 200,
        });
        const [isFocused, setIsFocused] = useState(false);

        const isControlled = controlledValue !== undefined;
        const value = isControlled ? controlledValue : internalValue;

        useImperativeHandle(ref, () => ({
            focus: () => textareaRef.current?.focus(),
            textareaRef: textareaRef as React.RefObject<HTMLTextAreaElement>,
            adjustHeight,
        }));

        const handleSubmit = () => {
            if (onSubmit) {
                onSubmit();
            } else {
                setInternalValue("");
                adjustHeight(true);
            }
        };

        const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
            if (onChange) {
                onChange(e);
            } else {
                setInternalValue(e.target.value);
            }
            adjustHeight();
        };

        const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
            if (onKeyDown) {
                onKeyDown(e);
            } else if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
            }
        };

        const handleContainerClick = () => {
            if (textareaRef.current) {
                textareaRef.current.focus();
            }
        };

        return (
            <div className={cn("w-full py-4 px-4", className)}>
                <div className="relative w-full">
                    <div
                        role="textbox"
                        tabIndex={0}
                        aria-label="Chat input container"
                        className={cn(
                            "relative flex flex-col rounded-xl transition-all duration-200 w-full text-left cursor-text",
                            "border border-border bg-muted/50",
                            isFocused && "border-primary/50 ring-1 ring-primary/20"
                        )}
                        onClick={handleContainerClick}
                    >
                        <div className="overflow-y-auto max-h-[200px]">
                            <Textarea
                                id="ai-input-chat"
                                value={value}
                                placeholder={placeholder}
                                className="w-full rounded-xl rounded-b-none px-4 py-3 bg-transparent border-none text-foreground placeholder:text-muted-foreground resize-none focus-visible:ring-0 leading-[1.2]"
                                ref={textareaRef}
                                onFocus={() => setIsFocused(true)}
                                onBlur={() => setIsFocused(false)}
                                onKeyDown={handleKeyDown}
                                onChange={handleChange}
                                disabled={disabled}
                            />
                        </div>

                        <div className="h-12 bg-muted/30 rounded-b-xl">
                            <div className="absolute left-3 bottom-3 flex items-center gap-2">
                                {leftActions}
                            </div>
                            <div className="absolute right-3 bottom-3">
                                <button
                                    type="button"
                                    onClick={handleSubmit}
                                    disabled={disabled || !value?.trim()}
                                    className={cn(
                                        "rounded-lg p-2 transition-colors cursor-pointer",
                                        value?.trim()
                                            ? "bg-primary text-primary-foreground hover:bg-primary/90"
                                            : "bg-muted text-muted-foreground",
                                        (disabled || !value?.trim()) && "opacity-50 cursor-not-allowed"
                                    )}
                                >
                                    <ArrowUp className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
);

AIInputSearch.displayName = "AIInputSearch";

export default AIInputSearch;
