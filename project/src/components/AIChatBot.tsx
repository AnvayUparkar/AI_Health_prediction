import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send, User, Bot, Loader2, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'model';
  content: string;
}

const SUGGESTED_PROMPTS = [
  "Why am I feeling tired lately?",
  "How can I improve my heart health?",
  "Can you give me tips for better sleep?",
  "What foods help reduce cholesterol?",
  "How do I manage daily stress?"
];

export const AIChatBot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load history from session storage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem('chatHistory');
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load chat history:", e);
      }
    } else {
      // Set initial greeting
      const greeting: Message = {
        role: 'model',
        content: "Hello! I am Dr. AI, a senior medical consultant. How can I help you today?\n\n*Note: I can provide health guidance, but I cannot prescribe medication. Please seek emergency services if you are experiencing a severe issue.*"
      };
      setMessages([greeting]);
      sessionStorage.setItem('chatHistory', JSON.stringify([greeting]));
    }
  }, []);

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    const userMsg: Message = { role: 'user', content: text };
    
    // We send up to the last 5 messages as history to keep the payload tight
    // Excluding the new user message we are about to append locally
    const historyPayload = messages.slice(-5);
    
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInputText("");
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: text,
          history: historyPayload
        })
      });

      const data = await response.json();
      
      const botMsg: Message = { 
        role: 'model', 
        content: data.response || "I'm having trouble connecting right now. Please try again later."
      };
      
      const updatedMessages = [...newMessages, botMsg];
      setMessages(updatedMessages);
      sessionStorage.setItem('chatHistory', JSON.stringify(updatedMessages));
      
    } catch (error) {
      console.error("Chat error:", error);
      const errorMsg: Message = { 
        role: 'model', 
        content: "Sorry, I am unable to connect to the medical knowledge base at the moment."
      };
      const updatedMessages = [...newMessages, errorMsg];
      setMessages(updatedMessages);
      sessionStorage.setItem('chatHistory', JSON.stringify(updatedMessages));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend(inputText);
    }
  };

  const token = localStorage.getItem('token');
  if (!token) return null; // Don't render for guests

  return (
    <>
      {/* Floating Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 p-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full shadow-2xl hover:shadow-[0_0_20px_rgba(37,99,235,0.5)] transition-all flex items-center justify-center group"
          >
            <MessageCircle className="h-7 w-7 group-hover:scale-110 transition-transform" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Modal */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="fixed bottom-6 right-6 z-50 w-[380px] h-[600px] max-h-[85vh] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-4 flex items-center justify-between text-white">
              <div className="flex items-center space-x-3">
                <div className="bg-white/20 p-2 rounded-full">
                  <Bot className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold">Dr. AI Assistant</h3>
                  <p className="text-xs text-blue-100">Senior Medical Consultant</p>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-white/20 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 flex flex-col">
              {messages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] rounded-2xl p-3 shadow-sm ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-br-none' 
                      : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                  }`}>
                    {msg.role === 'model' && msg.content.includes('⚠️') ? (
                      <div className="flex items-start space-x-2 text-red-600 mb-2 font-semibold">
                         <AlertCircle className="h-5 w-5 shrink-0" />
                         <span>URGENT ALERT</span>
                      </div>
                    ) : null}
                    
                    <div className={msg.role === 'user' ? 'text-sm whitespace-pre-wrap' : 'text-sm prose prose-sm max-w-none prose-p:leading-snug prose-a:text-blue-600'}>
                      {msg.role === 'user' ? (
                        msg.content
                      ) : (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white text-gray-500 border border-gray-100 rounded-2xl rounded-bl-none p-4 shadow-sm flex items-center space-x-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-xs font-medium">Dr. AI is typing...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested Prompts */}
            {!isLoading && (
              <div className="px-4 pb-2 bg-gray-50 flex flex-nowrap overflow-x-auto space-x-2 hide-scrollbar">
                {SUGGESTED_PROMPTS.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(prompt)}
                    className="shrink-0 bg-white border border-gray-200 text-blue-600 text-xs px-3 py-1.5 rounded-full hover:bg-blue-50 hover:border-blue-300 transition-colors whitespace-nowrap"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            {/* Input Footer */}
            <div className="p-3 bg-white border-t border-gray-100 flex items-center space-x-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about your health..."
                disabled={isLoading}
                className="flex-1 bg-gray-100 text-sm rounded-full px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:opacity-50"
              />
              <button
                onClick={() => handleSend(inputText)}
                disabled={!inputText.trim() || isLoading}
                className="p-2.5 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="h-5 w-5 ml-0.5" />
              </button>
            </div>
            
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
