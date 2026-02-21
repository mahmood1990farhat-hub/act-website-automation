"use client";

import React from "react";
import ModernLoading from "./ModernLoading";

type PageLoadingProps = {
  message?: string;
  variant?: "default" | "minimal" | "fullscreen";
};

export default function PageLoading({
  message = "Loading...",
  variant = "default",
}: PageLoadingProps) {
  if (variant === "minimal") {
    return (
      <div className="w-full min-h-[200px] flex items-center justify-center py-8">
        <ModernLoading size="md" variant="spinner" text={message} />
      </div>
    );
  }

  if (variant === "fullscreen") {
    return (
      <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-foreground rounded-2xl p-8 shadow-2xl border-2 border-primary/20">
          <ModernLoading size="lg" variant="pulse" text={message} />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-[60vh] flex items-center justify-center py-16">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <ModernLoading size="lg" variant="spinner" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-8 h-8 rounded-full bg-primary/20 animate-pulse"></div>
          </div>
        </div>
        <div className="text-center space-y-2">
          <p className="text-lg font-semibold text-primary">{message}</p>
          <div className="flex items-center gap-1 justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0s" }}></div>
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0.2s" }}></div>
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0.4s" }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

