import React from "react";

interface BeehiveMascotProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  showText?: boolean;
}

export const BeehiveMascot: React.FC<BeehiveMascotProps> = ({
  size = "md",
  className = "",
  showText = false,
}) => {
  const scale = size === "sm" ? 0.65 : size === "lg" ? 1.3 : 1.0;

  return (
    <div
      className={`beehive-mascot-container ${className}`}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        userSelect: "none",
      }}
    >
      <div
        className="beehive-stage"
        style={{
          position: "relative",
          width: `${240 * scale}px`,
          height: `${200 * scale}px`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Left Bee */}
        <div
          className="mascot-bee bee-left"
          style={{
            position: "absolute",
            left: `${15 * scale}px`,
            top: `${100 * scale}px`,
            transform: `scale(${scale})`,
          }}
          title="Worker Bee"
        >
          <svg width="34" height="30" viewBox="0 0 34 30" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Wing 1 */}
            <ellipse
              cx="13"
              cy="7"
              rx="6"
              ry="4"
              transform="rotate(-25 13 7)"
              fill="#FFFFFF"
              fillOpacity="0.85"
              stroke="#2E2822"
              strokeWidth="1.2"
              className="bee-wing-flutter"
            />
            {/* Wing 2 */}
            <ellipse
              cx="19"
              cy="6"
              rx="6"
              ry="4"
              transform="rotate(-5 19 6)"
              fill="#FFFFFF"
              fillOpacity="0.7"
              stroke="#2E2822"
              strokeWidth="1.2"
              className="bee-wing-flutter-delayed"
            />
            {/* Body */}
            <ellipse cx="16" cy="18" rx="10" ry="7" fill="#F4A325" stroke="#221E19" strokeWidth="1.6" />
            {/* Stripes */}
            <rect x="12" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
            <rect x="18" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
            {/* Head */}
            <circle cx="25" cy="18" r="4.2" fill="#241F1A" />
            <circle cx="26" cy="17" r="1" fill="#FFFFFF" />
            {/* Antennae */}
            <path d="M26.5 14C27.5 11 29 10 31 10.5" stroke="#241F1A" strokeWidth="1.2" strokeLinecap="round" />
            {/* Stinger */}
            <path d="M6 18L3.5 18" stroke="#241F1A" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </div>

        {/* Central Beehive */}
        <div
          className="mascot-hive"
          style={{
            transform: `scale(${scale})`,
            filter: "drop-shadow(0 6px 16px rgba(180, 115, 20, 0.2))",
          }}
        >
          <svg width="150" height="136" viewBox="0 0 150 136" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="hiveGrad" x1="75" y1="0" x2="75" y2="136" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#EDB03D" />
                <stop offset="50%" stopColor="#E5A12D" />
                <stop offset="100%" stopColor="#D48B1C" />
              </linearGradient>
              <linearGradient id="entranceGrad" x1="75" y1="58" x2="75" y2="92" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#F6C34C" />
                <stop offset="100%" stopColor="#E39F28" />
              </linearGradient>
            </defs>

            {/* Hive Tier 1 (top) */}
            <rect x="52" y="10" width="46" height="16" rx="8" fill="url(#hiveGrad)" />
            {/* Hive Tier 2 */}
            <rect x="36" y="24" width="78" height="18" rx="9" fill="url(#hiveGrad)" />
            {/* Hive Tier 3 */}
            <rect x="25" y="40" width="100" height="20" rx="10" fill="url(#hiveGrad)" />
            {/* Hive Tier 4 (widest) */}
            <rect x="18" y="58" width="114" height="22" rx="11" fill="url(#hiveGrad)" />
            {/* Hive Tier 5 */}
            <rect x="25" y="78" width="100" height="20" rx="10" fill="url(#hiveGrad)" />
            {/* Hive Tier 6 */}
            <rect x="36" y="96" width="78" height="18" rx="9" fill="url(#hiveGrad)" />
            {/* Hive Tier 7 (bottom) */}
            <rect x="52" y="112" width="46" height="14" rx="7" fill="url(#hiveGrad)" />

            {/* Entrance / Honey Pot door */}
            <path
              d="M68 62C68 57.58 71.13 54 75 54C78.87 54 82 57.58 82 62V82C82 85.31 79.31 88 76 88H74C70.69 88 68 85.31 68 82V62Z"
              fill="url(#entranceGrad)"
              stroke="#D48B1C"
              strokeWidth="1.2"
            />
            {/* Inner entrance notch */}
            <rect x="71" y="65" width="8" height="20" rx="4" fill="#C57E12" />
          </svg>
        </div>

        {/* Right Bee */}
        <div
          className="mascot-bee bee-right"
          style={{
            position: "absolute",
            right: `${15 * scale}px`,
            top: `${42 * scale}px`,
            transform: `scale(${scale})`,
          }}
          title="QA / Research Bee"
        >
          <svg width="34" height="30" viewBox="0 0 34 30" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Wing 1 */}
            <ellipse
              cx="19"
              cy="7"
              rx="6"
              ry="4"
              transform="rotate(25 19 7)"
              fill="#FFFFFF"
              fillOpacity="0.85"
              stroke="#2E2822"
              strokeWidth="1.2"
              className="bee-wing-flutter"
            />
            {/* Wing 2 */}
            <ellipse
              cx="13"
              cy="6"
              rx="6"
              ry="4"
              transform="rotate(5 13 6)"
              fill="#FFFFFF"
              fillOpacity="0.7"
              stroke="#2E2822"
              strokeWidth="1.2"
              className="bee-wing-flutter-delayed"
            />
            {/* Body */}
            <ellipse cx="16" cy="18" rx="10" ry="7" fill="#F4A325" stroke="#221E19" strokeWidth="1.6" />
            {/* Stripes */}
            <rect x="13" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
            <rect x="19" y="11.5" width="3.2" height="13" rx="1.6" fill="#241F1A" />
            {/* Head (facing left) */}
            <circle cx="7" cy="18" r="4.2" fill="#241F1A" />
            <circle cx="6" cy="17" r="1" fill="#FFFFFF" />
            {/* Antennae */}
            <path d="M6 14C5 11 3.5 10 1.5 10.5" stroke="#241F1A" strokeWidth="1.2" strokeLinecap="round" />
            {/* Stinger */}
            <path d="M26 18L28.5 18" stroke="#241F1A" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </div>
      </div>

      {showText && (
        <div style={{ textAlign: "center", marginTop: "12px" }}>
          <h3
            style={{
              fontSize: "16px",
              fontWeight: 700,
              color: "#2E2822",
              letterSpacing: "-0.3px",
              marginBottom: "4px",
            }}
          >
            The Hive is Standing By
          </h3>
          <p style={{ fontSize: "12px", color: "#7A6C58", maxWidth: "340px", lineHeight: "1.4" }}>
            Start the demo scenario or send instructions to the Queen to watch the swarm research, build, and verify in real time.
          </p>
        </div>
      )}
    </div>
  );
};
