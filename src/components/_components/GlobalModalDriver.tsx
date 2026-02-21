"use client";
import React from "react";

export default function GlobalModalDriver({
  isOpen,
  onClose,
  children,
}: {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
className="fixed inset-0 bg-black/10 bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        onClick={(e) => e.stopPropagation()}
      className="bg-white p-3 rounded-md w-full max-w-md relative shadow-lg  max-h-[100vh] overflow-y-auto no-scrollbar text-center space-y-4 pb-4 pt-8 text-lg"
      >
        {children}
      </div>
    </div>
  );
}
