# EduSync UI/UX Local Testing Guide

This guide helps you test the UI/UX locally without requiring the backend to be deployed.

---

## Quick Start

### 1. Start Local Server

```bash
cd /Users/sir/edusync-netlify
./test-local.sh
```

Or manually with Python:

```bash
cd /Users/sir/edusync-netlify/static
python3 -m http.server 8080
```

### 2. Open Test Environment

- **Main Site:** http://localhost:8080
- **UI Test Panel:** http://localhost:8080/test-ui.html

---

## What's Included

### Mock API System (`static/js/mock-api.js`)

A client-side JavaScript mock that intercepts API calls and returns fake data:

```javascript
// Automatically handles these endpoints:
GET  /api/health              → Health check
GET  /api/v1/homework         → List homework
POST /api/v1/homework         → Create homework
GET  /api/v1/users/:id        → Get user
GET  /api/v1/students/:id/*   → Student data
```

**Features:**
- No server required - runs entirely in browser
- Simulates network delay (100-300ms)
- Persists data in memory during session
- Logs all API calls to console

### Test UI Panel (`static/test-ui.html`)

Interactive testing interface with:

1. **API Test Panel** - Test each endpoint individually
2. **Component Library** - View all UI components
3. **Live Mock Data** - Interactive data loading
4. **UI/UX Checklist** - Testing checklist
5. **Test Console** - Real-time logs

---

## UI/UX Testing Checklist

### Responsive Design

Test these breakpoints:

| Device | Width | Test |
|--------|-------|------|
| Mobile S | 320px | iPhone SE size |
| Mobile M | 375px | iPhone 12 size |
| Mobile L | 425px | Large phones |
| Tablet | 768px | iPad portrait |
| Desktop | 1024px+ | Full screen |

**How to test:**
1. Open Chrome DevTools (F12)
2. Toggle Device Toolbar (Ctrl+Shift+M)
3. Select preset or enter custom size

### Visual Testing

- [ ] **Typography**: Fonts readable, sizes consistent
- [ ] **Colors**: Brand colors applied, good contrast
- [ ] **Spacing**: Padding/margins consistent
- [ ] **Shadows**: Elevation consistent on cards
- [ ] **Borders**: Radius and width consistent

### Interaction States

Test each interactive element:

| Element | Default | Hover | Active/Focus | Disabled |
|---------|---------|-------|--------------|----------|
| Primary Button | ✓ | ✓ | ✓ | ✓ |
| Secondary Button | ✓ | ✓ | ✓ | ✓ |
| Text Input | ✓ | - | ✓ (blue border) | ✓ |
| Cards | ✓ | ✓ (lift) | - | - |
| Links | ✓ | ✓ | ✓ | ✓ |

**How to test:**
1. Hover over elements
2. Click and hold to see active state
3. Tab through elements to see focus state
4. Check disabled state where applicable

### Data States

| State | Visual Indicator | Test |
|-------|-----------------|------|
| Loading | Spinner animation | Click "Load Homework" |
| Empty | Empty message/card | Clear data and refresh |
| Error | Red text/border | Check console for errors |
| Success | Green checkmark | Add homework successfully |
| Overdue | Red left border | Look at mock homework |

### Accessibility (A11y)

```bash
# Install axe DevTools Chrome extension
# Or use Lighthouse in DevTools
```

- [ ] **Color contrast**: 4.5:1 for normal text
- [ ] **Focus indicators**: Visible keyboard focus
- [ ] **Alt text**: Images have descriptions
- [ ] **ARIA labels**: Interactive elements labeled
- [ ] **Keyboard nav**: Can tab through all interactive elements

### Performance (Local)

- [ ] **Load time**: < 3 seconds for initial render
- [ ] **Images**: Optimized, lazy loaded
- [ ] **No layout shift**: Elements don't jump during load

---

## Testing Scenarios

### Scenario 1: Parent Viewing Homework

1. Go to http://localhost:8080/test-ui.html
2. Click "Load Homework"
3. Verify:
   - Cards display correctly
   - Subject colors are correct
   - Due dates formatted properly
   - Priority badges visible
   - Overdue items highlighted in red

### Scenario 2: Adding New Homework

1. Click "+ Add Homework" button
2. Wait for success
3. Verify:
   - New item appears in list
   - Correct subject/title shown
   - Animation/transition smooth
   - Stats update correctly

### Scenario 3: Empty State

1. Refresh page
2. Clear console
3. Don't click load buttons
4. Verify placeholder text shows

### Scenario 4: Mobile Experience

1. Open DevTools
2. Set to iPhone 12 Pro (390x844)
3. Test:
   - Scroll smooth
   - Touch targets > 44px
   - Text readable without zoom
   - No horizontal scroll

---

## Browser Testing

| Browser | Version | Test Status |
|---------|---------|-------------|
| Chrome | Latest | ✓ |
| Firefox | Latest | ⬜ |
| Safari | Latest | ⬜ |
| Edge | Latest | ⬜ |
| Mobile Chrome | iOS/Android | ⬜ |
| Mobile Safari | iOS | ⬜ |

---

## Debugging Tips

### Check Mock API Data

```javascript
// In browser console:
console.table(mockDB.homework)  // View all homework
console.log(mockDB.user)        // View user data
console.log(mockDB.stats)       // View stats
```

### Monitor API Calls

All API calls are logged to:
1. Browser console
2. Test Console in test-ui.html

### Force Refresh

```bash
# Clear browser cache
Ctrl + Shift + R  # Hard reload
```

### Check for JavaScript Errors

```javascript
// In console, watch for:
// - Red error messages
// - Failed fetch requests
// - Undefined variables
```

---

## Customizing Mock Data

Edit `static/js/mock-api.js`:

```javascript
const mockDB = {
    homework: [
        // Add your test data here
        {
            id: '1',
            subject: 'Custom Subject',
            title: 'Custom Title',
            // ...
        }
    ]
};
```

---

## File Structure

```
static/
├── index.html          # Main landing page
├── test-ui.html        # UI testing panel
└── js/
    └── mock-api.js     # Mock API interceptor
```

---

## Next Steps After UI Testing

1. **Fix any UI issues** found during testing
2. **Document changes** in changelog
3. **Update main index.html** with improvements
4. **Push to GitHub** when ready
5. **Then** work on backend deployment separately

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8080 in use | `PORT=3000 ./test-local.sh` |
| Mock API not working | Check console for errors, refresh page |
| Changes not showing | Hard refresh (Ctrl+Shift+R) |
| CORS errors | Use local server, not file:// protocol |
| Console empty | Check DevTools console filter |

---

## Resources

- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Responsive Design Guide](https://web.dev/responsive-web-design-basics/)

---

*Happy Testing! 🎨*
