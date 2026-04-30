"use client";

import React from "react";

type ModernLoadingProps = {
  size?: "sm" | "md" | "lg";
  variant?: "spinner" | "dots" | "pulse" | "bars";
  className?: string;
  text?: string;
};

export default function ModernLoading({
  size = "md",
  variant = "spinner",
  className = "",
  text,
}: ModernLoadingProps) {
  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-12 w-12",
    lg: "h-16 w-16",
  };

  const textSizeClasses = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg",
  };

  const renderLoader = () => {
    switch (variant) {
      case "dots":
        return (
          <div className="flex items-center gap-2">
            <div className={`${sizeClasses[size]} rounded-full bg-primary animate-pulse`} style={{ animationDelay: "0s" }}></div>
            <div className={`${sizeClasses[size]} rounded-full bg-primary animate-pulse`} style={{ animationDelay: "0.2s" }}></div>
            <div className={`${sizeClasses[size]} rounded-full bg-primary animate-pulse`} style={{ animationDelay: "0.4s" }}></div>
          </div>
        );

      case "pulse":
        return (
          <div className={`${sizeClasses[size]} rounded-full bg-primary/20 relative`}>
            <div className={`absolute inset-0 rounded-full bg-primary animate-ping`}></div>
            <div className={`absolute inset-2 rounded-full bg-primary/60`}></div>
          </div>
        );

      case "bars":
        return (
          <div className="flex items-end gap-1.5 h-12">
            <div className="w-2 bg-primary rounded-t loading-bar" style={{ animationDelay: "0s", height: "20%" }}></div>
            <div className="w-2 bg-primary rounded-t loading-bar" style={{ animationDelay: "0.1s", height: "40%" }}></div>
            <div className="w-2 bg-primary rounded-t loading-bar" style={{ animationDelay: "0.2s", height: "60%" }}></div>
            <div className="w-2 bg-primary rounded-t loading-bar" style={{ animationDelay: "0.3s", height: "80%" }}></div>
            <div className="w-2 bg-primary rounded-t loading-bar" style={{ animationDelay: "0.4s", height: "100%" }}></div>
          </div>
        );

      default: // spinner
        return (
          <div className={`${sizeClasses[size]} relative`}>
            <div className="absolute inset-0 rounded-full border-4 border-primary/20"></div>
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin"></div>
            <div className="absolute inset-2 rounded-full border-2 border-primary/10"></div>
          </div>
        );
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-4 ${className}`}>
      {renderLoader()}
      {text && (
        <p className={`${textSizeClasses[size]} text-muted-foreground font-medium animate-pulse`}>
          {text}
        </p>
      )}
    </div>
  );
}

