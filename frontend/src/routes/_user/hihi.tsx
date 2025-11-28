

import { faker } from '@faker-js/faker';
import {
    KanbanBoard,
    KanbanCard,
    KanbanCards,
    KanbanHeader,
    KanbanProvider,
} from '@/components/ui/shadcn-io/kanban';
import { useState } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { createFileRoute } from '@tanstack/react-router'
import AI_Input_Search from '@/components/kokonutui/ai-input-search';
import {
    PromptInput,
    PromptInputButton,
    PromptInputModelSelect,
    PromptInputModelSelectContent,
    PromptInputModelSelectItem,
    PromptInputModelSelectTrigger,
    PromptInputModelSelectValue,
    PromptInputSubmit,
    PromptInputTextarea,
    PromptInputToolbar,
    PromptInputTools,
} from '@/components/ui/shadcn-io/ai/prompt-input';
import { MicIcon, PaperclipIcon } from 'lucide-react';
import { type FormEventHandler } from 'react';
const models = [
    { id: 'gpt-4o', name: 'GPT-4o' },
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
];

export const Route = createFileRoute('/_user/hihi')({
    component: RouteComponent,
})


function RouteComponent() {
    const [text, setText] = useState<string>('');
    const [model, setModel] = useState<string>(models[0].id);
    const [status, setStatus] = useState<
        'submitted' | 'streaming' | 'ready' | 'error'
    >('ready');
    const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
        event.preventDefault();
        if (!text) {
            return;
        }
        setStatus('submitted');
        setTimeout(() => {
            setStatus('streaming');
        }, 200);
        setTimeout(() => {
            setStatus('ready');
            setText('');
        }, 2000);
    };


    return (
        <>
            <div className='p-8 w-full'>
                <PromptInput onSubmit={handleSubmit}>
                    <PromptInputTextarea
                        onChange={(e) => setText(e.target.value)}

                        value={text}
                        placeholder="Type your message..."
                    />
                    <PromptInputToolbar>
                        <PromptInputTools>
                            <PromptInputButton>
                                <PaperclipIcon size={16} />
                            </PromptInputButton>

                        </PromptInputTools>
                        <PromptInputSubmit disabled={!text} status={status} />
                    </PromptInputToolbar>
                </PromptInput>
            </div>
        </>
    )
}
