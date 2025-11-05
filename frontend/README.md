# CargoDham AI Frontend

React + TypeScript frontend for the multi-tenant AI logistics platform.

## Features

- **Autonomous Chat Interface** - Natural language commands that trigger real API calls
- **Real-time Updates** - See AI actions and API calls in real-time
- **Beautiful UI** - Modern design with Tailwind CSS + Framer Motion animations
- **Type-Safe** - Full TypeScript support
- **Fast Development** - Vite for lightning-fast HMR

## Tech Stack

- **React 18** - Latest React with hooks
- **TypeScript** - Full type safety
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Axios** - API communication
- **Vite** - Build tool and dev server

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:3000

### Build

```bash
npm run build
```

## Project Structure

```
src/
├── features/               # Feature-based organization
│   └── chat/              # Chat feature
│       └── components/    # Chat components
│           ├── ChatContainer.tsx
│           ├── ChatMessageBubble.tsx
│           ├── SuggestedCommands.tsx
│           └── APICallsPanel.tsx
├── lib/                   # Shared libraries
│   └── api/              # API clients
│       └── chat.ts
├── App.tsx               # Main app component
├── main.tsx              # Entry point
└── index.css             # Global styles
```

## Usage

### Chat with AI

The chat interface connects to the backend's autonomous execution system:

```typescript
// User types: "Book shipment from Mumbai to Delhi"
// AI automatically:
// 1. Classifies intent (CREATE_BOOKING)
// 2. Extracts entities (origin, destination)
// 3. Calls partner APIs
// 4. Returns result
```

### Setting Tenant ID

```typescript
import { chatAPI } from '@/lib/api/chat';

chatAPI.setTenantId('your-tenant-id');
```

## Components

### ChatContainer

Main chat interface with message list and input.

### ChatMessageBubble

Individual message bubble with intent, entities, and API call display.

### SuggestedCommands

Shows example commands based on partner capabilities.

### APICallsPanel

Displays API calls made by the AI with status indicators.

## API Integration

The frontend communicates with the backend REST API:

- `POST /api/chat/message` - Send message for autonomous execution
- `GET /api/chat/capabilities` - Get available operations

## Environment Variables

Create `.env.local`:

```
VITE_API_URL=http://localhost:8000/api
```

## Styling

Using Tailwind CSS with custom color palette:

```typescript
// Primary colors
bg-primary-500  // Main brand color
bg-primary-600  // Darker variant
bg-primary-700  // Even darker
```

## Animations

Using Framer Motion for smooth transitions:

```typescript
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -20 }}
>
  ...
</motion.div>
```

## Future Enhancements

- [ ] Partner onboarding wizard
- [ ] Document upload with drag-and-drop
- [ ] Real-time parsing progress
- [ ] Integration viewer
- [ ] Partner dashboard
- [ ] Dynamic booking forms
- [ ] Multi-partner selection
- [ ] Session persistence
- [ ] Voice input
- [ ] Mobile responsive improvements

## Contributing

This is part of the CargoDham AI platform. See main README for contribution guidelines.

## License

Private - All rights reserved

