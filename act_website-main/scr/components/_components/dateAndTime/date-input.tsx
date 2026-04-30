"use client";

import { useEffect, useState } from "react";
import { CalendarIcon } from "lucide-react";
// import { format } from "date-fns"
import { ar, enUS } from "date-fns/locale";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { DatePicker } from "./date-picker";
import { format } from "date-fns";

type Language = "ar" | "en";

const placeholders = {
  ar: "اختر التاريخ",
  en: "Select date",
};

interface DateInputProps {
  placeholder?: string;
  value?: Date;
  onChange?: (date: Date) => void;
  className?: string;
  language?: Language;
  setFormattedDate?: (formattedDate: string) => void;
  required?: boolean;
  inCreateCaptain?: true;
}

  function getOrdinal(n:number) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

export function DateInput({
  placeholder,
  value,
  onChange,
  required,
  className,
  inCreateCaptain,
  language = "ar",
  setFormattedDate,
}: DateInputProps) {
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const defaultPlaceholder = placeholder || placeholders[language];
  const locale = language === "ar" ? ar : enUS;
  const isRTL = language === "ar";

  const handleDateSelect = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();

    const formattedDate = `${year}-${month}-${day}`;
    setFormattedDate && setFormattedDate(formattedDate);
    onChange?.(date);

    setIsPickerOpen(false);
  };


  const formatDate = (date: Date) => {
    if (language === "ar") {
      return format(date, "d/M/yyyy", { locale });
    } else {
       const day = date.getDate();
    const monthYear = format(date, "MMMM yyyy", { locale });
    return `${day}${getOrdinal(day)} ${monthYear}`;
  }


  };

  return (
    <>
      {!inCreateCaptain && (
        <button

    type="button"
          onClick={() => setIsPickerOpen(true)}
          className={cn(
            `flex items-center w-full justify-start h-12  p-2.5 mb-2 border-2 bg-white text-foreground font-semibold rounded-lg ${
              required && !value ? "border-red-700" : ""
            }`,
            !value && "",
            className,
            isRTL ? "text-right" : "text-left"
          )}
          dir={isRTL ? "rtl" : "ltr"}
        >
          <CalendarIcon className={cn("h-4 w-4", isRTL ? "ml-2" : "mr-2")} />
          {value ? formatDate(value) : <span className="text-gray-400">{defaultPlaceholder}</span>}
        </button>
      )}

      <DatePicker
        inCreateCaptain={inCreateCaptain}
        isOpen={isPickerOpen || inCreateCaptain}
        onClose={() => setIsPickerOpen(false)}
        onSelect={handleDateSelect}
        selectedDate={value}
        onCancel={() => setIsPickerOpen(false)}
        language={language}
      />
    </>
  );
}
