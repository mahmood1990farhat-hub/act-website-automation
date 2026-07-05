"use client";

import { useState } from "react";
import { Clock } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ActTimePicker } from "./act-time-picker";

type Language = "ar" | "en";

interface TimeValue {
  hour: number;
  minute: number;
}

const placeholders = {
  ar: "اختر الوقت",
  en: "Select time",
};

interface TimeInputProps {
  id?: string;
  placeholder?: string;
  value?: TimeValue;
  onChange?: (time: TimeValue) => void;
  className?: string;
  language?: Language;
  required?: boolean;
  setFormattedTime?: (time: string) => void;
  inCreateCaptain?: true;
}

export function TimeInput({
  id,
  placeholder,
  value,
  onChange,
  className,
  language = "ar",
  required,
  inCreateCaptain,
  setFormattedTime,
}: TimeInputProps) {
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const defaultPlaceholder = placeholder || placeholders[language];
  const isRTL = language === "ar";

  const handleTimeSelect = (time: TimeValue) => {
    onChange?.(time);
    setFormattedTime?.(
      `${time.hour.toString().padStart(2, "0")}:${time.minute
        .toString()
        .padStart(2, "0")}`
    );
    setIsPickerOpen(false);
  };

  const formatTime = (time: TimeValue) => {
    if (!time) return "";

    const hour = time.hour % 12 || 12;
    const period = time.hour >= 12 ? "PM" : "AM";

    return `${hour}:${time.minute.toString().padStart(2, "0")} ${period}`;
  };

  return (
    <>
      {!inCreateCaptain && (
        <button
          id={id}
          type="button"
          onClick={() => setIsPickerOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={isPickerOpen}
          className={cn(
            `flex items-center w-full justify-start h-12 p-2.5 mb-2 border-2 border-[#ffd100]/70 bg-white text-foreground font-semibold rounded-lg shadow-sm transition-colors hover:border-[#ffd100] focus:outline-none focus:ring-2 focus:ring-[#ffd100]/40 ${
              required && !value ? "border-red-700" : ""
            }`,
            !value && "",
            className,
            isRTL ? "text-right" : "text-left"
          )}
          dir={isRTL ? "rtl" : "ltr"}
        >
          <Clock className={cn("h-5 w-5 text-[#9a7d00]", isRTL ? "ml-2" : "mr-2")} />
          {value ? formatTime(value) : <span className="text-gray-400">{defaultPlaceholder}</span>}
        </button>
      )}

      <ActTimePicker
        inCreateCaptain={inCreateCaptain}
        isOpen={isPickerOpen || inCreateCaptain}
        onClose={() => setIsPickerOpen(false)}
        onSelect={handleTimeSelect}
        selectedTime={value}
        onCancel={() => setIsPickerOpen(false)}
        language={language}
      />
    </>
  );
}
