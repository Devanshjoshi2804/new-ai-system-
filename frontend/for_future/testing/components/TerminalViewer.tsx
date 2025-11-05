/**
 * Terminal Viewer Component
 * Displays real-time test logs in a terminal-style UI
 */
import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { TestLogEvent, LogLevel } from '../../../types/testEvents';
import 'xterm/css/xterm.css';

interface TerminalViewerProps {
  logs: TestLogEvent[];
  autoScroll?: boolean;
  className?: string;
}

export const TerminalViewer: React.FC<TerminalViewerProps> = ({
  logs,
  autoScroll = true,
  className = ''
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const lastLogIndexRef = useRef(0);

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current) return;

    // Create terminal instance
    const terminal = new Terminal({
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#d4d4d4',
        cursorAccent: '#1e1e1e',
        selection: 'rgba(255, 255, 255, 0.3)',
        black: '#000000',
        red: '#f48771',
        green: '#4ec9b0',
        yellow: '#dcdcaa',
        blue: '#569cd6',
        magenta: '#c586c0',
        cyan: '#4ec9b0',
        white: '#d4d4d4',
        brightBlack: '#808080',
        brightRed: '#f48771',
        brightGreen: '#4ec9b0',
        brightYellow: '#dcdcaa',
        brightBlue: '#569cd6',
        brightMagenta: '#c586c0',
        brightCyan: '#4ec9b0',
        brightWhite: '#ffffff'
      },
      fontSize: 13,
      fontFamily: '"Fira Code", "Consolas", "Monaco", monospace',
      fontWeight: '400',
      fontWeightBold: '700',
      cursorBlink: false,
      cursorStyle: 'block',
      scrollback: 10000,
      tabStopWidth: 4,
      convertEol: true,
      disableStdin: true,
      allowProposedApi: true
    });

    // Add fit addon
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);

    // Add web links addon
    const webLinksAddon = new WebLinksAddon();
    terminal.loadAddon(webLinksAddon);

    // Open terminal
    terminal.open(terminalRef.current);
    fitAddon.fit();

    // Store references
    xtermRef.current = terminal;
    fitAddonRef.current = fitAddon;

    // Handle window resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        try {
          fitAddonRef.current.fit();
        } catch (error) {
          console.error('Error fitting terminal:', error);
        }
      }
    };

    window.addEventListener('resize', handleResize);

    // Initial welcome message
    terminal.writeln('\x1b[36m╔══════════════════════════════════════════════════════════════╗\x1b[0m');
    terminal.writeln('\x1b[36m║          🧪 AI-Powered API Testing Terminal                 ║\x1b[0m');
    terminal.writeln('\x1b[36m╚══════════════════════════════════════════════════════════════╝\x1b[0m');
    terminal.writeln('');

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      terminal.dispose();
    };
  }, []);

  // Write logs to terminal
  useEffect(() => {
    if (!xtermRef.current || logs.length === 0) return;

    const terminal = xtermRef.current;

    // Write only new logs
    for (let i = lastLogIndexRef.current; i < logs.length; i++) {
      const log = logs[i];
      const color = getLogColor(log.data.level);
      const icon = getLogIcon(log.data.level);
      
      // Format message with color and icon
      terminal.writeln(`${color}${icon} ${log.data.message}\x1b[0m`);
    }

    // Update last log index
    lastLogIndexRef.current = logs.length;

    // Auto-scroll to bottom
    if (autoScroll) {
      terminal.scrollToBottom();
    }
  }, [logs, autoScroll]);

  return (
    <div className={`terminal-container ${className}`}>
      <div
        ref={terminalRef}
        className="terminal-wrapper"
        style={{
          height: '100%',
          width: '100%',
          padding: '8px'
        }}
      />
      <style>{`
        .terminal-container {
          background-color: #1e1e1e;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .terminal-wrapper {
          font-variant-ligatures: none;
        }
        .xterm {
          padding: 8px;
        }
        .xterm-viewport {
          overflow-y: auto !important;
        }
        .xterm-viewport::-webkit-scrollbar {
          width: 8px;
        }
        .xterm-viewport::-webkit-scrollbar-track {
          background: #2d2d2d;
        }
        .xterm-viewport::-webkit-scrollbar-thumb {
          background: #555;
          border-radius: 4px;
        }
        .xterm-viewport::-webkit-scrollbar-thumb:hover {
          background: #666;
        }
      `}</style>
    </div>
  );
};

// Helper functions
function getLogColor(level: LogLevel): string {
  switch (level) {
    case LogLevel.SUCCESS:
      return '\x1b[32m'; // Green
    case LogLevel.ERROR:
      return '\x1b[31m'; // Red
    case LogLevel.WARNING:
      return '\x1b[33m'; // Yellow
    case LogLevel.INFO:
    default:
      return '\x1b[36m'; // Cyan
  }
}

function getLogIcon(level: LogLevel): string {
  switch (level) {
    case LogLevel.SUCCESS:
      return '✓';
    case LogLevel.ERROR:
      return '✗';
    case LogLevel.WARNING:
      return '⚠';
    case LogLevel.INFO:
    default:
      return '•';
  }
}
