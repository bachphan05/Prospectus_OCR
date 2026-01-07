/**
 * HighlightBox Component - Renders a highlighted bounding box overlay with tooltip
 * @param {Array} bbox - Bounding box [ymin, xmin, ymax, xmax] in 0-1000 scale
 * @param {string} label - Field name/label
 * @param {*} value - Extracted value to display in tooltip
 * @param {boolean} isHighlighted - Whether this box should be highlighted (from UI hover)
 */
const HighlightBox = ({ bbox, label, value, isHighlighted = false }) => {
  if (!bbox || bbox.length !== 4) return null;

  const [ymin, xmin, ymax, xmax] = bbox;

  // Convert 0-1000 scale to CSS percentages
  const style = {
    top: `${ymin / 10}%`,
    left: `${xmin / 10}%`,
    width: `${(xmax - xmin) / 10}%`,
    height: `${(ymax - ymin) / 10}%`,
  };

  return (
    <div
      className={`absolute border-2 transition-all cursor-pointer group z-10 ${
        isHighlighted 
          ? 'border-blue-600 bg-blue-400 bg-opacity-50 animate-pulse' 
          : 'border-yellow-500 bg-yellow-300 bg-opacity-20 hover:bg-opacity-40'
      }`}
      style={style}
    >
      {/* Tooltip on Hover */}
      <div className="hidden group-hover:block absolute bottom-full left-0 mb-1 bg-black text-white text-xs p-1 rounded whitespace-nowrap z-20 shadow-lg">
        <span className="font-bold">{label}:</span> {String(value)}
      </div>
    </div>
  );
};

export default HighlightBox;
