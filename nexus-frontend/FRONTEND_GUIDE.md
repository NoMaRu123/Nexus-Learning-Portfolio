# Nexus — Full Setup & Frontend Build Guide

This guide covers everything from setting up your database to building the React frontend. Follow it top to bottom.

---

## Part 0: Backend Setup (Do This First)

Before touching the frontend, you need the backend running. That means PostgreSQL + environment variables.

---

### 0.1 Install PostgreSQL

You need a PostgreSQL database. The easiest option on Windows:

**Option A — Docker Desktop (Recommended if you want to learn containers)**

1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install it and restart your PC if prompted
3. Open PowerShell and run:

```powershell
docker run -d --name nexus-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=nexus -p 5432:5432 postgres:15
```

That's it. You now have PostgreSQL running on port 5432 with:
- Username: `postgres`
- Password: `postgres`
- Database name: `nexus`

To check it's running: `docker ps` (you should see `nexus-db` listed).

To stop it later: `docker stop nexus-db`
To start it again: `docker start nexus-db`

**Option B — Install PostgreSQL directly**

1. Download from: https://www.postgresql.org/download/windows/
2. Run the installer — use the default port (5432)
3. When it asks for a password, pick something simple like `postgres` (this is local dev only)
4. After install, open **pgAdmin** (installed with PostgreSQL) or PowerShell:

```powershell
# Open the PostgreSQL command line (psql) — it's in your PATH after install
psql -U postgres
```

5. Create the database:

```sql
CREATE DATABASE nexus;
\q
```

Now you have PostgreSQL running with:
- Username: `postgres`
- Password: whatever you set during install
- Database name: `nexus`

---

### 0.2 Configure Your .env File

Open `nexus-backend/.env` and fill in these values:

```env
# === REQUIRED ===

# Mode: "tracker" for local dev, "portfolio" for public deployment
NEXUS_MODE=tracker

# Database connection string
# Format: postgresql+asyncpg://USERNAME:PASSWORD@HOST:PORT/DATABASE
# If you used Docker with the command above:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/nexus

# JWT secret — this can be any long random string. It's used to sign login tokens.
# Generate one by running this in PowerShell:
#   python -c "import secrets; print(secrets.token_hex(32))"
# Or just use this for local dev:
JWT_SECRET=my-super-secret-dev-key-change-in-production-12345

# Allowed frontend origins for CORS
CORS_ORIGINS=http://localhost:5173

# === OPTIONAL (leave blank for now) ===

JWT_EXPIRY_MINUTES=60
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./uploads
LLM_PROVIDER=
OPENAI_API_KEY=
OPENAI_MODEL=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
WEBHOOK_URL=
WEBHOOK_AUTH_HEADER=
```

**What each required value means:**

| Variable | What it is | How to get it |
|----------|-----------|---------------|
| `DATABASE_URL` | Connection string to your PostgreSQL | If you used Docker above, it's exactly `postgresql+asyncpg://postgres:postgres@localhost:5432/nexus` |
| `JWT_SECRET` | A random string used to sign login tokens | Run `python -c "import secrets; print(secrets.token_hex(32))"` in PowerShell, or just use any long string for dev |
| `CORS_ORIGINS` | Which URLs can talk to your backend | `http://localhost:5173` (that's where Vite runs the frontend) |

---

### 0.3 Run the Backend

Open PowerShell, navigate to the backend folder, and run:

```powershell
cd C:\Users\ASUS\OneDrive\Repo\LearningTracker\nexus-backend

# Activate the Python virtual environment
.\.venv\Scripts\Activate.ps1

# Apply database migrations (creates all the tables)
alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

If everything worked, visit http://localhost:8000/docs — you should see the interactive API documentation.

> **Troubleshooting:**
> - "connection refused" → PostgreSQL isn't running. Start Docker (`docker start nexus-db`) or start the PostgreSQL service.
> - "database does not exist" → Create it: `docker exec nexus-db psql -U postgres -c "CREATE DATABASE nexus;"`
> - "execution policy" error on Activate.ps1 → Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` first.

---

### 0.4 Keep the Backend Running

Leave that PowerShell window open with the backend running. Open a **new** PowerShell window for the frontend work below.

---
---

## Part 1: Frontend Build Guide

This section walks you through building the React/Chakra UI frontend from scratch. Each step builds on the previous one.

---

## Prerequisites

- Node.js 18+ installed (you have v23.3.0 ✓)
- The backend running at `http://localhost:8000` (from Part 0 above)
- A code editor (VS Code)

---

## Step 1: Create the Project

Open a **PowerShell** terminal and navigate to the `nexus-frontend/` directory:

```powershell
cd C:\Users\ASUS\OneDrive\Repo\LearningTracker\nexus-frontend
```

> **Important**: The guide file (FRONTEND_GUIDE.md) is already in this folder. Vite may warn about a non-empty directory. If it does, temporarily move the guide out, create the project, then move it back. Or use the `--force` flag:

```powershell
npm create vite@latest . -- --template react-ts
npm install
```

If prompted "Current directory is not empty", select "Ignore files and continue".

This gives you a React + TypeScript project powered by Vite.

**Verify it works:**
```powershell
npm run dev
```
Visit `http://localhost:5173` — you should see the Vite + React starter page. Press `Ctrl+C` to stop the dev server when done checking.

---

## Step 2: Install Dependencies

```powershell
npm install @chakra-ui/react @emotion/react @emotion/styled framer-motion
npm install react-router-dom axios react-easy-crop
npm install -D @types/react-easy-crop
```

| Package | Purpose |
|---------|---------|
| `@chakra-ui/react` | UI component library (tiles, forms, layout) |
| `@emotion/react` + `@emotion/styled` | CSS-in-JS (required by Chakra) |
| `framer-motion` | Animations (required by Chakra) |
| `react-router-dom` | Page routing |
| `axios` | HTTP client for talking to the backend |
| `react-easy-crop` | Profile picture cropping (1:1 ratio) |

---

## Step 3: Set Up Environment Variables

Create a `.env` file in the project root:

```env
VITE_API_URL=http://localhost:8000
VITE_NEXUS_MODE=tracker
```

Create a `.env.example` with the same keys (no values) for version control.

> In Vite, env vars must start with `VITE_` to be accessible in the browser.

---

## Step 4: Project Structure

Organize your `src/` folder like this:

```
src/
├── components/       # Reusable UI pieces (Tiles, ChatWidget, etc.)
├── pages/            # Full page components (Dashboard, Login, etc.)
├── context/          # React context providers (Auth, Mode)
├── services/         # API client layer
├── hooks/            # Custom React hooks
├── utils/            # Helper functions (image processing, debounce)
├── types/            # TypeScript interfaces
├── App.tsx           # Root component with routing
└── main.tsx          # Entry point (wraps with providers)
```

Create these folders now in PowerShell:

```powershell
New-Item -ItemType Directory -Path src/components, src/pages, src/context, src/services, src/hooks, src/utils, src/types -Force
```

They'll be empty at first and that's fine.

---

## Step 5: Wrap the App with Chakra + Providers

**`src/main.tsx`**
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChakraProvider } from '@chakra-ui/react'
import { BrowserRouter } from 'react-router-dom'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChakraProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ChakraProvider>
  </React.StrictMode>
)
```

---

## Step 6: Create the API Client

**`src/services/api.ts`**
```tsx
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Automatically attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
```

This is the single point of contact with your backend. Every API call goes through this.

---

## Step 7: Create the Auth Context

**`src/context/AuthContext.tsx`**
```tsx
import { createContext, useContext, useState, ReactNode } from 'react'
import api from '../services/api'

interface AuthContextType {
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('auth_token')
  )

  const login = async (email: string, password: string) => {
    const res = await api.post('/api/auth/login', { email, password })
    const newToken = res.data.data.access_token
    localStorage.setItem('auth_token', newToken)
    setToken(newToken)
  }

  const register = async (email: string, password: string) => {
    await api.post('/api/auth/register', { email, password })
    // Auto-login after registration
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setToken(null)
  }

  return (
    <AuthContext.Provider
      value={{ token, isAuthenticated: !!token, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

---

## Step 8: Create the Mode Context

**`src/context/ModeContext.tsx`**
```tsx
import { createContext, useContext, ReactNode } from 'react'

interface ModeContextType {
  isTrackerMode: boolean
  isPortfolioMode: boolean
}

const ModeContext = createContext<ModeContextType>({
  isTrackerMode: true,
  isPortfolioMode: false,
})

export function ModeProvider({ children }: { children: ReactNode }) {
  const mode = import.meta.env.VITE_NEXUS_MODE || 'tracker'

  return (
    <ModeContext.Provider
      value={{
        isTrackerMode: mode === 'tracker',
        isPortfolioMode: mode === 'portfolio',
      }}
    >
      {children}
    </ModeContext.Provider>
  )
}

export const useMode = () => useContext(ModeContext)
```

---

## Step 9: Define TypeScript Types

**`src/types/index.ts`**
```tsx
export interface Skill {
  id: string
  name: string
  category: string
  proficiency_level: string
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description: string | null
  status: string
  technology_tags: string[]
  created_at: string
  updated_at: string
}

export interface LearningEntry {
  id: string
  skill_id: string | null
  project_id: string | null
  description: string
  metadata: Record<string, string> | null
  timestamp: string
}

export interface UserProfile {
  id: string
  name: string | null
  bio: string | null
  contact_email: string | null
  social_links: Record<string, string> | null
  picture_url: string | null
}
```

---

## Step 10: Build the Login Page

**`src/pages/Login.tsx`**
```tsx
import { useState } from 'react'
import {
  Box, Button, Input, VStack, Heading, Text, Link,
} from '@chakra-ui/react'
import { useAuth } from '../context/AuthContext'
import { useNavigate, Link as RouterLink } from 'react-router-dom'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid email or password')
    }
  }

  return (
    <Box maxW="400px" mx="auto" mt="100px" p={6}>
      <Heading mb={6}>Log In</Heading>
      <form onSubmit={handleSubmit}>
        <VStack spacing={4}>
          <Input
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <Text color="red.500">{error}</Text>}
          <Button type="submit" colorScheme="blue" w="full">
            Log In
          </Button>
          <Text>
            No account?{' '}
            <Link as={RouterLink} to="/register" color="blue.500">
              Register
            </Link>
          </Text>
        </VStack>
      </form>
    </Box>
  )
}
```

Create a similar `src/pages/Register.tsx` — same form but calls `register()` instead.

---

## Step 11: Build the Dashboard

**`src/pages/Dashboard.tsx`**
```tsx
import { useEffect, useState } from 'react'
import {
  Box, SimpleGrid, Input, Select, HStack, Heading,
} from '@chakra-ui/react'
import api from '../services/api'
import { Skill, Project } from '../types'
import SkillTile from '../components/SkillTile'
import ProjectTile from '../components/ProjectTile'

export default function Dashboard() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData()
    }, 300) // 300ms debounce
    return () => clearTimeout(timer)
  }, [search, category])

  const fetchData = async () => {
    const params: Record<string, string> = {}
    if (search) params.q = search
    if (category) params.category = category

    const res = await api.get('/api/search', { params })
    // Separate skills from projects based on response
    setSkills(res.data.data.skills || [])
    setProjects(res.data.data.projects || [])
  }

  return (
    <Box p={6}>
      <Heading mb={6}>Dashboard</Heading>

      <HStack mb={6} spacing={4}>
        <Input
          placeholder="Search skills & projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select
          placeholder="All categories"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {/* Populate with categories from your data */}
        </Select>
      </HStack>

      <SimpleGrid columns={[1, 2, 3]} spacing={4}>
        {skills.map((skill) => (
          <SkillTile key={skill.id} skill={skill} />
        ))}
        {projects.map((project) => (
          <ProjectTile key={project.id} project={project} />
        ))}
      </SimpleGrid>
    </Box>
  )
}
```

---

## Step 12: Build Tile Components

**`src/components/SkillTile.tsx`**
```tsx
import { Card, CardBody, Heading, Text, Badge } from '@chakra-ui/react'
import { useNavigate } from 'react-router-dom'
import { Skill } from '../types'

export default function SkillTile({ skill }: { skill: Skill }) {
  const navigate = useNavigate()

  return (
    <Card
      cursor="pointer"
      onClick={() => navigate(`/skills/${skill.id}`)}
      _hover={{ shadow: 'lg' }}
    >
      <CardBody>
        <Heading size="sm">{skill.name}</Heading>
        <Text fontSize="sm" color="gray.500">{skill.category}</Text>
        <Badge mt={2} colorScheme="green">{skill.proficiency_level}</Badge>
      </CardBody>
    </Card>
  )
}
```

**`src/components/ProjectTile.tsx`** — same pattern but shows `project.name`, `project.status`, and `project.technology_tags` as badges.

---

## Step 13: Set Up Routing

**`src/App.tsx`**
```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ModeProvider } from './context/ModeContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import SkillDetail from './pages/SkillDetail'
import ProjectDetail from './pages/ProjectDetail'
import Profile from './pages/Profile'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

export default function App() {
  return (
    <AuthProvider>
      <ModeProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={
            <ProtectedRoute><Dashboard /></ProtectedRoute>
          } />
          <Route path="/skills/:id" element={
            <ProtectedRoute><SkillDetail /></ProtectedRoute>
          } />
          <Route path="/projects/:id" element={
            <ProtectedRoute><ProjectDetail /></ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute><Profile /></ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </ModeProvider>
    </AuthProvider>
  )
}
```

---

## Step 14: Build Detail Pages

Create `src/pages/SkillDetail.tsx` and `src/pages/ProjectDetail.tsx`:

- Fetch the record by ID from the URL params (`useParams()`)
- Fetch learning entries for that record (paginated, 10 per page)
- Display all fields
- Add a "Back to Dashboard" button
- In Tracker Mode, add an inline form to create new learning entries

---

## Step 15: Build the Profile Page

**Key features:**
1. Form with fields: name, bio, contact email, social links
2. Profile picture upload:
   - File input accepting `.jpg`, `.png`, `.webp` (max 5 MB)
   - When a file is selected, show the `react-easy-crop` component with 1:1 aspect ratio
   - On confirm, compress/resize to 512×512 using a canvas element
   - Upload the result to `POST /api/profile/picture`
3. Default placeholder avatar when no picture exists

**Canvas compression helper (`src/utils/imageUtils.ts`):**
```tsx
export async function compressImage(
  file: File,
  maxSize: number = 512
): Promise<Blob> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = maxSize
      canvas.height = maxSize
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(img, 0, 0, maxSize, maxSize)
      canvas.toBlob(
        (blob) => resolve(blob!),
        'image/webp',
        0.85
      )
    }
    img.src = URL.createObjectURL(file)
  })
}
```

---

## Step 16: Build the Chat Widget

**`src/components/ChatWidget.tsx`**

- Floating button in the bottom-right corner (Chakra `IconButton`)
- Clicking it opens a chat panel
- Maintains message history in component state
- Sends messages to `POST /api/bot/chat` with the full history
- Displays responses (handles loading + error states)
- Available on all pages (render it in `App.tsx` outside of Routes)

---

## Step 17: Run and Test

```powershell
npm run dev
```

1. Register a new account
2. Log in
3. Add some skills and projects via the dashboard
4. Click tiles to see detail views
5. Update your profile and upload a picture
6. Try the chat widget

---

## Tips

- **Chakra UI docs**: https://chakra-ui.com/docs — great component examples
- **React Router docs**: https://reactrouter.com — for routing patterns
- **Start ugly, refine later** — get the data flowing first, then polish the UI
- **Check the backend OpenAPI docs** at `http://localhost:8000/docs` to see exact request/response shapes
- **Use the browser Network tab** to debug API calls

---

## What's Next?

Once the frontend is working in Tracker Mode:
1. Switch `VITE_NEXUS_MODE=portfolio` to test read-only mode
2. Style it up — colors, spacing, responsive breakpoints
3. Deploy frontend to Vercel/Netlify, backend to Railway/Render
