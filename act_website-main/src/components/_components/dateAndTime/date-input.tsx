"use client";
import { runtimeText } from "@/lib/customer-runtime";

import { useEffect, useState } from "react";
import { CalendarIcon } from "lucide-react";
// import { format } from "date-fns"
import { ar, enUS, fr, de, es, tr, zhCN } from "date-fns/locale";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { DatePicker } from "./date-picker";
import { format } from "date-fns";

import { dictionaryLocale, type SupportedLocale } from "../../../../i18n.config";
type Language = SupportedLocale;

const placeholders = {
  ar: "اختر التاريخ",
  en: "Select date",
  fr: "Choisir une date",
};

interface DateInputProps {
  id?: string;
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
  id,
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

  const defaultPlaceholder = placeholder || runtimeText(language, "selectDate");
  const locale = ({ar, en: enUS, fr, de, es, tr, "zh-CN": zhCN})[language];
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
    if (language !== "en" && language !== "ar") return new Intl.DateTimeFormat(language, { day: "numeric", month: "long", year: "numeric" }).format(date);
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
          id={id}

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


