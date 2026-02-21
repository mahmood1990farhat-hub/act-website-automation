"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChevronDown, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface YearPickerProps {
  value?: string;
  onChange: (year: string) => void;
  placeholder?: string;
  min?: number;
  max?: number;
  language?: "en" | "ar";
  error?: any;
  requiredMsg?: string;
  label?: string;
}

export default function YearPicker({
  value,
  onChange,
  placeholder,
  min = 1950,
  max = new Date().getFullYear(),
  language = "en",
  error,
  requiredMsg,
  label,
}: YearPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isRTL = language === "ar";

  // Generate years array
  const years = Array.from({ length: max - min + 1 }, (_, i) => max - i);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleYearSelect = (year: number) => {
    onChange(year.toString());
    setIsOpen(false);
  };

  return (
    <div className="w-full" ref={containerRef}>
      {label && (
        <label className="block mb-1 text-[16px] font-medium">
          {label} {requiredMsg && <span className="text-primary">*</span>}
        </label>
      )}
      
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            "w-full min-h-[48px] flex items-center justify-between p-3 border-2 bg-foreground border-muted rounded-lg cursor-pointer hover:border-primary/50 transition-colors",
            error && "border-red-500",
            isRTL ? "text-right" : "text-left"
          )}
          dir={isRTL ? "rtl" : "ltr"}
        >
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 " />
            <span className={cn(value ? "text-primary" : "text-primary")}>
              {value || placeholder || "Select year"}
            </span>
          </div>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-muted-foreground transition-transform",
              isOpen && "rotate-180"
            )}
          />
        </button>

        {isOpen && (
          <div
            className={cn(
              "absolute z-50 mt-2 w-full bg-foreground border border-muted rounded-lg shadow-lg max-h-[300px] overflow-y-auto on-scrollbar",
              isRTL ? "right-0" : "left-0"
            )}
            dir={isRTL ? "rtl" : "ltr"}
          >
            <div className="p-3">
              <div className="grid grid-cols-4 gap-2">
                {years.map((year) => (
                  <button
                    key={year}
                    type="button"
                    onClick={() => handleYearSelect(year)}
                    className={cn(
                      "px-3 py-2.5 text-sm rounded-md transition-all duration-200",
                      value === year.toString()
                        ? "bg-primary font-semibold shadow-md"
                        : "text-primary hover:bg-primary/20 hover:text-primary"
                    )}
                  >
                    {year}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {requiredMsg && error && (
        <p className="text-error text-sm mt-1">{error.message}</p>
      )}
    </div>
  );
}

