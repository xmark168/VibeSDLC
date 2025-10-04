import { Bot, Zap } from 'lucide-react';
import { useEffect, useState } from 'react'

export default function MultiAgentTeam() {
    const [agents, setAgents] = useState([
        { name: 'PO', active: false, color: 'text-blue-300' },
        { name: 'SM', active: false, color: 'text-green-300' },
        { name: 'Dev', active: false, color: 'text-yellow-300' },
        { name: 'QA', active: false, color: 'text-red-300' }
    ]);

    useEffect(() => {
        const interval = setInterval(() => {
            setAgents(prev => prev.map((agent, idx) => ({
                ...agent,
                active: Math.random() > 0.6
            })));
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className='flex-1 flex items-center justify-center'>
            <div className='grid grid-cols-2 gap-16'>
                {
                    agents.map((agent, idx) => (
                        <div key={idx} className="relative flex flex-col items-center">
                            <div className={`
                                relative transition-all duration-500 ease-in-out
                                ${agent.active
                                    ? 'scale-110 opacity-100 filter drop-shadow-[0_0_15px_rgba(255,255,255,0.7)]'
                                    : 'scale-100 opacity-40'
                                }
                            `}>
                                <Bot className={`w-16 h-16 ${agent.color} mb-2`} />

                                {agent.active && (
                                    <div className="absolute -top-2 -right-2">
                                        <Zap className="w-6 h-6 text-yellow-400 animate-bounce" />
                                    </div>
                                )}
                            </div>

                            <span className={`
                                font-bold text-lg text-center transition-all duration-500
                                ${agent.active
                                    ? 'text-white opacity-100 scale-110'
                                    : 'text-gray-400 opacity-60 scale-100'
                                }
                            `}>
                                {agent.name}
                            </span>
                        </div>
                    ))
                }
            </div>
        </div>
    )
}