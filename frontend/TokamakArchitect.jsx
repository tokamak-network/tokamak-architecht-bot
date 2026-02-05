import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Loader2, Sparkles } from 'lucide-react'; 

const TokamakArchitect = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { 
      role: 'assistant', 
      content: "Hello! I'm the Tokamak Architect. I can help you configure your L2 Rollup. Ask me about RPCs, Challenge Periods, or Block Times!" 
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage.content,
          history: messages 
        }),
      });
      
      const data = await response.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.response 
      }]);
    } catch (error) {
      console.error("Bot Error:", error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "⚠️ I'm having trouble reaching the knowledge base. Please check your connection." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans">
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-xl transition-all duration-300 flex items-center gap-2"
        >
          <Sparkles size={24} />
          <span className="font-semibold hidden md:block">Ask Architect</span>
        </button>
      )}

      {isOpen && (
        <div className="bg-white rounded-2xl shadow-2xl w-[380px] h-[600px] flex flex-col border border-gray-200 overflow-hidden animate-in slide-in-from-bottom-10 fade-in duration-300">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-4 flex justify-between items-center text-white">
            <div className="flex items-center gap-2">
              <div className="bg-white/20 p-2 rounded-lg">
                <Sparkles size={20} />
              </div>
              <div>
                <h3 className="font-bold text-sm">Tokamak Architect</h3>
                <span className="text-xs text-blue-100 flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  Online
                </span>
              </div>
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              className="hover:bg-white/20 p-1 rounded-full transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 bg-gray-50 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-tr-none'
                      : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white p-3 rounded-2xl rounded-tl-none border border-gray-100 shadow-sm flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin text-blue-600" />
                  <span className="text-xs text-gray-400">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 bg-white border-t border-gray-100">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask about deployment settings..."
                className="flex-1 bg-gray-100 border-transparent focus:bg-white focus:border-blue-500 rounded-xl px-4 py-3 text-sm outline-none transition-all"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white p-3 rounded-xl transition-colors"
              >
                <Send size={18} />
              </button>
            </div>
            <div className="text-center mt-2">
              <span className="text-[10px] text-gray-400">
                AI can make mistakes. Check docs for critical info.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TokamakArchitect;
