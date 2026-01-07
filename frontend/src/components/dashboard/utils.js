/**
 * Utility: Extract value from either structured or flat format
 * Handles both new Gemini format {value, page, bbox} and old Mistral format (plain string/number)
 * 
 * @param {*} field - The field data (can be object with {value, page, bbox} or plain value)
 * @returns {*} The extracted value or the field itself if already a plain value
 */
export const getValue = (field) => {
  if (field && typeof field === 'object' && 'value' in field) {
    return field.value; // New Gemini structured format
  }
  return field; // Old flat format or null/undefined
};

/**
 * Utility: Get page and bbox info from structured field
 * @param {*} field - The field data
 * @returns {Object|null} {page, bbox} or null if not available
 */
export const getFieldInfo = (field) => {
  if (field && typeof field === 'object' && 'page' in field && 'bbox' in field) {
    return { page: field.page, bbox: field.bbox };
  }
  return null;
};

/**
 * Utility: Recursively find all bounding boxes for a specific page
 * This function traverses the entire JSON tree and finds all fields that have
 * value, page, and bbox properties matching the given page number.
 * 
 * @param {Object} data - The extracted data object
 * @param {number} pageNumber - The page number to filter by
 * @returns {Array} Array of highlight objects with {id, bbox, label, value}
 */
export const getHighlightsForPage = (data, pageNumber) => {
  const highlights = [];

  const traverse = (obj, keyName = '') => {
    if (!obj || typeof obj !== 'object') return;

    // Check if this object is a "Field with Location" (has value, page, bbox)
    if (obj.page === pageNumber && Array.isArray(obj.bbox) && obj.bbox.length === 4) {
      highlights.push({
        id: keyName + '_' + Math.random(), // Unique ID for React key
        bbox: obj.bbox,
        label: keyName, // e.g., "fund_name"
        value: obj.value
      });
    }

    // Recursively check children
    Object.keys(obj).forEach(key => {
      // Skip metadata keys or pure values
      if (key !== 'bbox' && key !== 'page' && key !== 'value') {
        traverse(obj[key], key);
      }
    });
  };

  traverse(data);
  return highlights;
};
