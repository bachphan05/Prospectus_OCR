# Dashboard Component Structure

## Overview
The Dashboard component has been refactored into smaller, reusable components for better maintainability and code organization.

## Component Structure

```
components/
├── Dashboard.jsx                    # Main dashboard component (refactored)
├── Dashboard-old.jsx               # Original dashboard backup
├── FileUpload.jsx
└── dashboard/                      # Dashboard sub-components
    ├── index.js                    # Barrel export file
    ├── utils.js                    # Utility functions
    ├── HighlightBox.jsx           # PDF bounding box overlay
    ├── DataField.jsx              # Field display/edit component
    ├── ChangeLogTooltip.jsx       # Change history tooltip
    ├── DocumentListItem.jsx       # Document list item with change log badge
    ├── DocumentHeader.jsx         # Document detail header with actions
    ├── CommentInput.jsx           # User comment input for edits
    └── StatsBar.jsx               # Statistics display bar
```

## Component Descriptions

### Main Component
**Dashboard.jsx** (464 lines → refactored)
- Main container managing state and data flow
- Handles document loading, editing, and page navigation
- Coordinates between sub-components

### Sub-Components

#### utils.js
- `getValue()` - Extracts value from structured/flat format
- `getFieldInfo()` - Gets page and bbox info from field
- `getHighlightsForPage()` - Recursively finds all bboxes for a page

#### HighlightBox.jsx (40 lines)
- Renders bounding box overlays on PDF pages
- Shows tooltip with field label and value on hover
- Highlights when hovered from data field list

#### DataField.jsx (65 lines)
- Displays or edits individual data fields
- Handles hover interactions for PDF highlighting
- Supports both structured (Gemini) and flat (Mistral) formats

#### ChangeLogTooltip.jsx (58 lines)
- Shows detailed change history in tooltip
- Displays up to 3 field changes per log entry
- Shows user comments and timestamps

#### DocumentListItem.jsx (56 lines)
- Individual document item in the list
- Shows document name, status, fund info
- Interactive "Đã sửa X lần" badge with hover tooltip

#### DocumentHeader.jsx (106 lines)
- Document detail header with title and metadata
- Edit/Save/Cancel buttons
- Delete, Reprocess, and Download actions

#### CommentInput.jsx (20 lines)
- Input field for user comments during edit
- Only visible when in edit mode
- Optional field with helpful placeholder

#### StatsBar.jsx (41 lines)
- Displays 5 statistics cards
- Shows total, pending, processing, completed, failed counts
- Includes loading skeleton state

## Benefits of Refactoring

1. **Maintainability**: Each component has a single responsibility
2. **Reusability**: Components can be used independently
3. **Testability**: Smaller components are easier to test
4. **Readability**: Reduced file size from 1004 lines to ~464 lines
5. **Performance**: Easier to optimize individual components
6. **Developer Experience**: Easier to locate and modify specific features

## Import Usage

```javascript
// Import all components at once
import {
  HighlightBox,
  DataField,
  DocumentListItem,
  DocumentHeader,
  CommentInput,
  StatsBar,
  getHighlightsForPage
} from './dashboard/index';

// Or import individually
import HighlightBox from './dashboard/HighlightBox';
import { getValue } from './dashboard/utils';
```

## Migration Notes

- The old Dashboard.jsx has been backed up as Dashboard-old.jsx
- All functionality remains identical
- No breaking changes to parent components (App.jsx)
- All existing features work as before
