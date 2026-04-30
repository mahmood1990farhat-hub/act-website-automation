"use client";

import { useState } from "react";
import { Clock } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { TimePicker } from "./time-picker";

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

    return `${time.hour.toString().padStart(2, "0")}:${time.minute
      .toString()
      .padStart(2, "0")}`;
  };

  return (
    <>
      {!inCreateCaptain && (
        <button
          type="button"
          onClick={() => setIsPickerOpen(true)}
          className={cn(
            `flex items-center w-full justify-start h-12 p-2.5 mb-2 border-2 bg-white text-foreground font-semibold rounded-lg ${
              required && !value ? "border-red-700" : ""
            }`,
            !value && "",
            className,
            isRTL ? "text-right" : "text-left"
          )}
          dir={isRTL ? "rtl" : "ltr"}
        >
          <Clock className={cn("h-4 w-4", isRTL ? "ml-2" : "mr-2")} />
          {value ? formatTime(value) : <span className="text-gray-400">{defaultPlaceholder}</span>}
        </button>
      )}

      <TimePicker
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
