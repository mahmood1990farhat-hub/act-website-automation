import React from "react";

const MoneyCountingHand = () => {
  return (
    <div style={{ width: 150, height: 50 }}>
      <svg
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%" }}
      >
        {/* اليد */}
        <path
          d="M20 40 L30 25 L40 30 L35 45 Z"
          fill="#f5c6a5"
          stroke="#c47d58"
          strokeWidth="2"
        >
          <animateTransform
            attributeName="transform"
            type="translate"
            values="0 0; 5 0; 0 0"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </path>

        {/* النقود */}
        <rect
          x="25"
          y="30"
          width="15"
          height="10"
          fill="#4caf50"
          stroke="#2e7d32"
          strokeWidth="2"
          rx="2"
          ry="2"
        >
          <animateTransform
            attributeName="transform"
            type="translate"
            values="0 0; 0 -5; 0 0"
            dur="1.5s"
            repeatCount="indefinite"
            begin="0.75s"
          />
        </rect>

        {/* علامة الدولار */}
        <text
          x="32"
          y="37"
          fontSize="10"
          fill="white"
          fontWeight="bold"
          fontFamily="Arial, sans-serif"
          pointerEvents="none"
        >
          $
        </text>
      </svg>
    </div>
  );
};

export default MoneyCountingHand;
