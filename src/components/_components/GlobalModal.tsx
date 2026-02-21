"use client";
import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export default function GlobalModal({
  isOpen,
  onClose,
  children,
  maxWidth = "4xl",
}: {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
}) {
  const getMaxWidthClass = (width: string) => {
    switch (width) {
      case "sm":
        return "md:max-w-sm";
      case "md":
        return "md:max-w-md";
      case "lg":
        return "md:max-w-lg";
      case "xl":
        return "md:max-w-xl";
      case "2xl":
        return "md:max-w-2xl";
      case "3xl":
        return "md:max-w-3xl";
      case "4xl":
        return "md:max-w-4xl";
      default:
        return "md:max-w-4xl";
    }
  };
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen || !mounted) return null;

  const modalContent = (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[9999] p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`bg-card rounded-xl w-full max-w-[95vw] ${getMaxWidthClass(maxWidth)} relative shadow-2xl max-h-[90vh] overflow-y-auto on-scrollbar m-0`}
      >
        {children}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
