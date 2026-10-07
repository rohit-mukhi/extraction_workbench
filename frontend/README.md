# Extraction Workbench - Frontend

Next.js frontend for the Extraction Workbench application.

---

## Overview

This is a modern React application built with Next.js 14 (App Router) and TypeScript that provides:
- **Ticket browsing** with search and multi-select
- **Job creation** for batch extraction
- **Real-time progress** tracking with auto-refresh
- **Side-by-side review** interface for verifying extracted data
- **Inline editing** with validation
- **CSV export** functionality

---

## Technology Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety throughout
- **Tailwind CSS** - Utility-first styling
- **React Hooks** - State management
- **Fetch API** - Backend communication

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Home page (ticket list)
│   ├── globals.css             # Global styles
│   └── jobs/
│       └── [id]/
│           └── page.tsx        # Job detail & review page
│
├── lib/
│   ├── types.ts                # TypeScript interfaces
│   └── api.ts                  # API client functions
│
├── public/                     # Static assets
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
├── tailwind.config.ts          # Tailwind config
├── next.config.ts              # Next.js config
├── .env.example                # Environment template
├── .env.local                  # Local environment (gitignored)
└── README.md                   # This file
```

---

## Prerequisites

- **Node.js 18+** (includes npm)
- **Backend service** running at `http://localhost:8000`

---

## Installation

### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env.local

# Edit .env.local if backend is not at default URL
# Default: NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Running the Frontend

### Development Mode (with hot reload)

```bash
npm run dev
```

Frontend runs at: **http://localhost:3000**

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

### Type Checking

```bash
# Check TypeScript types
npm run type-check
```

### Linting

```bash
# Run ESLint
npm run lint
```

---

## Features & Pages

### Home Page (`/`)

**URL:** `http://localhost:3000`

**Features:**
- Lists all 150 support tickets
- Search by subject, body, email, or ticket ID
- Multi-select with checkboxes
- "Select All" and "Clear" buttons
- Shows selection count
- "Start Extraction" button creates job

**Components:**
- Ticket cards with preview
- Search input with live filtering
- Selection controls
- Loading states
- Error handling with retry

### Job Detail Page (`/jobs/[id]`)

**URL:** `http://localhost:3000/jobs/job_abc123`

**Features:**
- Real-time progress tracking (polls every 2 seconds)
- Progress bar with percentage
- Statistics: total, queued, running, completed, failed
- List of extracted records (left panel)
- Side-by-side review interface (right panel)
- Original ticket text display
- Inline field editing with validation
- "Human Edited" badges
- `needs_review` visual indicators (yellow border)
- CSV export button (when job completes)

**Components:**
- Progress dashboard
- Record list with selection
- Ticket display
- Field editors (text, select, number, date, checkbox)
- Edit/Save/Cancel controls

---

## API Integration

### API Client (`lib/api.ts`)

All backend communication goes through functions in `api.ts`:

```typescript
// Tickets
getTickets(params?: { limit?: number; search?: string })

// Jobs
createJob(ticketIds: string[])
getJob(jobId: string)
getJobResults(jobId: string)

// Records
updateRecord(recordId: string, field: string, value: any)

// Export
downloadCSV(jobId: string)

// Polling
pollJobStatus(jobId: string, onUpdate: (job) => void)
```

### Type Safety (`lib/types.ts`)

TypeScript interfaces match backend Pydantic models:
- `Ticket`
- `Job`
- `JobProgress`
- `ExtractedRecord`
- Enums: `ProductType`, `CategoryType`, `SeverityLevel`, etc.

---

## Environment Variables

### `.env.local` (Local Development)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### `.env.production` (Deployment)

```bash
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
```

**Note:** Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

---

## Styling

### Tailwind CSS

Utility classes used throughout for:
- Layout (flex, grid)
- Spacing (p-*, m-*)
- Colors (bg-*, text-*)
- Responsive design (sm:, md:, lg:)
- Hover/focus states

### Color Scheme

- **Primary:** Blue (bg-blue-600, text-blue-600)
- **Success:** Green (bg-green-100, text-green-800)
- **Warning:** Yellow (bg-yellow-100, text-yellow-800)
- **Danger:** Red (bg-red-100, text-red-800)
- **Neutral:** Gray (bg-gray-50, text-gray-600)

### Responsive Design

- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px)
- Single column on mobile, two columns on desktop (job page)

---

## State Management

### React Hooks Used

- `useState` - Local component state
- `useEffect` - Side effects (data fetching, polling)
- `use` - Async params unwrapping (Next.js 14)
- `useRouter` - Navigation

### Polling Strategy

Job detail page polls every 2 seconds while job is running:
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    if (job?.status === "running") {
      loadJobData();
    }
  }, 2000);
  return () => clearInterval(interval);
}, [job?.status]);
```

---

## Error Handling

### Network Errors

```typescript
try {
  const data = await getTickets();
  setTickets(data);
} catch (err) {
  setError(err.message);
  // Show error UI with retry button
}
```

### Validation Errors

Field updates are validated on the backend:
```typescript
try {
  await updateRecord(recordId, field, value);
} catch (err) {
  alert(err.message); // Shows user-friendly error
}
```

### CORS Issues

If you see CORS errors:
1. Check backend is running
2. Verify `NEXT_PUBLIC_API_URL` in `.env.local`
3. Ensure backend `CORS_ORIGINS` includes `http://localhost:3000`

---

## Development Tips

### Auto-Reload

Development server watches for file changes:
- Edit any `.tsx`, `.ts`, `.css` file
- Browser automatically refreshes
- State is preserved (Fast Refresh)

### TypeScript Errors

Fix TypeScript errors before running:
```bash
npm run type-check
```

Common errors:
- Missing types: Define in `lib/types.ts`
- Async/await: Mark functions as `async`
- Null checks: Use optional chaining (`?.`)

### Debugging

**Chrome DevTools:**
- Console: See errors and logs
- Network: Monitor API calls
- React DevTools: Inspect component state

**Common Issues:**

1. **Blank page:**
   - Check console for errors
   - Verify backend is running
   - Check `NEXT_PUBLIC_API_URL`

2. **API calls fail:**
   - Check Network tab
   - Verify backend responds to `http://localhost:8000`
   - Check CORS configuration

3. **State not updating:**
   - Check `useState` dependencies
   - Verify `useEffect` dependency array
   - Console.log state values

---

## Building for Production

### Local Production Build

```bash
# Build
npm run build

# Test production build locally
npm start
```

### Optimization

Next.js automatically:
- Minifies JavaScript/CSS
- Optimizes images
- Code splits by route
- Generates static pages where possible

---

## Deployment (Vercel)

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Frontend complete"
git push origin main
```

### Step 2: Deploy to Vercel

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repository
4. Configure:
   - **Root Directory:** `frontend`
   - **Framework:** Next.js (auto-detected)
   - **Build Command:** `npm run build` (auto)
   - **Output Directory:** `.next` (auto)
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com`
6. Click "Deploy"

### Step 3: Test Deployed Site

1. Visit your Vercel URL (e.g., `https://extraction-workbench.vercel.app`)
2. Check browser console for errors
3. Test full workflow:
   - Load tickets
   - Create job
   - Review records
   - Export CSV

---

## Troubleshooting

### Port 3000 Already in Use

```bash
# Kill existing process
lsof -i :3000
kill -9 <PID>

# Or use different port
npm run dev -- -p 3001
```

### Module Not Found

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json .next
npm install
```

### Build Fails

```bash
# Check TypeScript errors
npm run type-check

# Check for syntax errors
npm run lint

# Clear Next.js cache
rm -rf .next
npm run build
```

### Environment Variables Not Working

- Variables MUST start with `NEXT_PUBLIC_` to be exposed to browser
- Restart dev server after changing `.env.local`
- Check spelling and capitalization exactly match

### CORS Errors in Production

Update backend environment:
```bash
CORS_ORIGINS=https://your-frontend.vercel.app
```

Redeploy backend after changing.

---

## Testing

### Manual Testing Checklist

**Home Page:**
- [ ] All tickets load without errors
- [ ] Search filters tickets correctly
- [ ] Checkbox selection works
- [ ] Select All selects filtered tickets
- [ ] Clear button works
- [ ] Start Extraction button is disabled when no selection
- [ ] Clicking Start Extraction redirects to job page

**Job Page:**
- [ ] Progress bar appears and updates
- [ ] Statistics are accurate
- [ ] Records appear as they complete
- [ ] Clicking record shows detail view
- [ ] Original ticket text displays correctly
- [ ] All fields are editable
- [ ] Edit/Save/Cancel work correctly
- [ ] Human Edited badge appears after edit
- [ ] needs_review items have yellow border
- [ ] Export CSV button appears when done
- [ ] CSV downloads correctly

**Error Handling:**
- [ ] Shows error if backend is down
- [ ] Retry button reloads data
- [ ] Validation errors show on invalid input

---

## Performance

### Optimization Techniques

- **Code splitting:** Each page loads only needed JavaScript
- **Lazy loading:** Images and components load on demand
- **Memoization:** Expensive calculations cached
- **Debouncing:** Search input debounced (could add)
- **Pagination:** Could add for large ticket lists

### Bundle Size

```bash
# Analyze bundle size
npm run build
# Check .next/static for file sizes
```

---

## Accessibility

### Current Features

- Semantic HTML (`<button>`, `<input>`, etc.)
- Keyboard navigation (Tab, Enter)
- ARIA labels on interactive elements
- Focus indicators (blue ring)
- Color contrast meets WCAG AA

### Future Improvements

- Keyboard shortcuts (e.g., Ctrl+S to save)
- Screen reader announcements
- Skip to content links
- Better focus management in modals

---

## Browser Support

- **Chrome:** Latest 2 versions ✅
- **Firefox:** Latest 2 versions ✅
- **Safari:** Latest 2 versions ✅
- **Edge:** Latest 2 versions ✅
- **Mobile:** iOS Safari, Chrome Android ✅

---

## Dependencies

### Production

- `next` - React framework
- `react` - UI library
- `react-dom` - DOM rendering
- `tailwindcss` - CSS framework

### Development

- `typescript` - Type checking
- `@types/node` - Node.js types
- `@types/react` - React types
- `eslint` - Linting
- `eslint-config-next` - Next.js ESLint config

---

## File Conventions

### Naming

- **Pages:** `page.tsx` (Next.js App Router convention)
- **Components:** PascalCase (e.g., `RecordField.tsx`)
- **Types:** `types.ts`
- **Utilities:** `api.ts`, `helpers.ts`

### Code Style

- 2-space indentation
- Double quotes for strings
- Semicolons required
- Trailing commas in objects/arrays

---

## Future Enhancements

### Short-term

- [ ] Debounced search input
- [ ] Pagination for ticket list
- [ ] Filter by channel, date range
- [ ] Sort records by status, company, etc.
- [ ] Keyboard shortcuts

### Long-term

- [ ] Dark mode toggle
- [ ] User authentication
- [ ] Multiple jobs dashboard
- [ ] Real-time updates (WebSocket)
- [ ] Advanced filtering
- [ ] Bulk record editing
- [ ] Export format options (JSON, Excel)

---

## Contributing

When adding features:

1. **Types first:** Update `lib/types.ts`
2. **API next:** Add function to `lib/api.ts`
3. **UI last:** Update page/component
4. **Test:** Manual testing checklist
5. **Commit:** Clear, descriptive message

---

## Links

- **Root README:** `../README.md`
- **Backend README:** `../backend/README.md`
- **Architecture Decisions:** `../DECISIONS.md`
- **Next.js Docs:** https://nextjs.org/docs
- **Tailwind Docs:** https://tailwindcss.com/docs

---

## Support

For issues:
1. Check console for errors
2. Verify backend is running
3. Check environment variables
4. Review troubleshooting section
5. See root README for full setup

---

## License

See repository root for license information.
