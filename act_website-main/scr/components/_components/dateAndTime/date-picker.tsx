"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Edit3 } from "lucide-react";
import {
  format,
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameDay,
  isToday,
  startOfDay,
} from "date-fns";
import { ar, enUS } from "date-fns/locale";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const translations = {
  ar: {
    selectDate: "اختر التاريخ",
    close: "إغلاق",
    cancel: "إلغاء",
    ok: "موافق",
    months: [
      "يناير",
      "فبراير",
      "مارس",
      "أبريل",
      "مايو",
      "يونيو",
      "يوليو",
      "أغسطس",
      "سبتمبر",
      "أكتوبر",
      "نوفمبر",
      "ديسمبر",
    ],
    days: ["ح", "ن", "ث", "ر", "خ", "ج", "س"],
  },
  en: {
    selectDate: "Select date",
    close: "Close",
    cancel: "Cancel",
    ok: "OK",
    months: [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ],
    days: ["S", "M", "T", "W", "T", "F", "S"],
  },
};

type Language = "ar" | "en";

interface MobileDatePickerProps {
  isOpen?: boolean;
  onClose: () => void;
  onSelect: (date: Date) => void;
  selectedDate?: Date;
  onCancel?: () => void;
  language?: Language;
  inCreateCaptain?: true;
}

export function DatePicker({
  isOpen,
  onClose,
  onSelect,
  selectedDate,
  inCreateCaptain,
  onCancel,
  language = "ar",
}: MobileDatePickerProps) {
  const [currentMonth, setCurrentMonth] = useState(selectedDate || new Date());
  const [tempSelectedDate, setTempSelectedDate] = useState<Date | undefined>(
    selectedDate
  );

  if (!isOpen) return null;

  const t = translations[language];
  const locale = language === "ar" ? ar : enUS;
  const isRTL = language === "ar";
  const today = new Date();

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

  const firstDayOfWeek = monthStart.getDay();
  const emptyCells = Array.from({ length: firstDayOfWeek }, (_, i) => i);

  const handleDateClick = (date: Date) => {
    setTempSelectedDate(date);
  };

  const handleOK = () => {
    if (tempSelectedDate) {
      onSelect(tempSelectedDate);
    }
    onClose();
  };

  const handleCancel = () => {
    setTempSelectedDate(selectedDate);
    onCancel?.();
    onClose();
  };

  const formatSelectedDate = (date: Date) => {
    if (language === "ar") {
      const dayName = format(date, "EEEE", { locale });
      const dayNumber = format(date, "d");
      const monthName = t.months[date.getMonth()];
      return `${dayName}، ${dayNumber} ${monthName}`;
    } else {
      return format(date, "EEE, MMM d", { locale });
    }
  };

  return inCreateCaptain ? (
    <div
      className="bg-gray-100 rounded-3xl p-6 w-full max-w-sm mx-auto"
      dir={isRTL ? "rtl" : "ltr"}
    >
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-sm text-gray-600 mb-3">{t.selectDate}</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-2xl font-medium  text-gray-900">
              {tempSelectedDate
                ? formatSelectedDate(tempSelectedDate)
                : t.selectDate}
            </div>
          </div>
          <Edit3 className="w-5 h-5 text-gray-500" />
        </div>
      </div>

      {/* Month Navigation */}
      <div className="flex items-center justify-between mb-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            setCurrentMonth(
              isRTL ? addMonths(currentMonth, 1) : subMonths(currentMonth, 1)
            )
          }
          className="p-2"
        >
          <ChevronLeft className="w-4 h-4 text-black" />
        </Button>

        <div className="text-base font-medium text-muted-foreground">
          {t.months[currentMonth.getMonth()]} {currentMonth.getFullYear()}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            setCurrentMonth(
              isRTL ? subMonths(currentMonth, 1) : addMonths(currentMonth, 1)
            )
          }
          className="p-2"
        >
          <ChevronRight className="w-4 h-4 text-black" />
        </Button>
      </div>

      {/* Days of Week Header */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {t.days.map((day, index) => (
          <div
            key={`${day}-${index}`}
            className="text-center text-sm text-gray-500 py-2 font-medium"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1 mb-6">
        {emptyCells.map((_, index) => (
          <div key={`empty-${index}`} className="h-10" />
        ))}

        {daysInMonth.map((date: Date) => {
          const isSelected =
            tempSelectedDate && isSameDay(date, tempSelectedDate);
          const isTodayDate = isToday(date);
          const isPastDate = date < startOfDay(today);

          return (
            <button
              key={date.toISOString()}
              onClick={() => !isPastDate && handleDateClick(date)}
              disabled={isPastDate}
              className={cn(
                "h-10 w-10 rounded-full text-sm font-medium transition-colors",
                "hover:bg-gray-200 focus:outline-none text-black focus:ring-2 focus:ring-yellow-400",
                {
                  "bg-yellow-400 text-black": isSelected,
                  "ring-2 ring-yellow-400": isTodayDate && !isSelected,
                  "text-gray-900": !isSelected && !isTodayDate,
                  "opacity-40 cursor-not-allowed": isPastDate,
                }
              )}
            >
              {format(date, "d")}
            </button>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className={cn("flex justify-between text-black", isRTL && "flex-row-reverse")}>
        <Button
          variant="ghost"
          onClick={onClose}
          className=" hover:text-gray-800"
        >
          {t.close}
        </Button>

        <div dir="ltr" className="flex gap-2">
          <Button
            variant="ghost"
            onClick={handleCancel}
            className=" hover:text-gray-800"
          >
            {t.cancel}
          </Button>
          <Button
            onClick={handleOK}
            className="bg-gray-800 text-white hover:bg-gray-900 px-6"
          >
            {t.ok}
          </Button>
        </div>
      </div>
    </div>
  ) : (
    <div onClick={onClose} className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div
        className="bg-gray-100 rounded-3xl p-6 w-full max-w-sm mx-auto"
        dir={isRTL ? "rtl" : "ltr"}
        onClick={(e)=>e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-sm text-gray-600 mb-3">{t.selectDate}</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-medium  text-gray-900">
                {tempSelectedDate
                  ? formatSelectedDate(tempSelectedDate)
                  : t.selectDate}
              </div>
            </div>
            <Edit3 className="w-5 h-5 text-gray-500" />
          </div>
        </div>

        {/* Month Navigation */}
        <div className="flex items-center justify-between mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setCurrentMonth(
                isRTL ? addMonths(currentMonth, 1) : subMonths(currentMonth, 1)
              )
            }
            className="p-2"
          >
            <ChevronLeft className="w-4 h-4 text-black" />
          </Button>

          <div className="text-base font-medium text-muted-foreground">
            {t.months[currentMonth.getMonth()]} {currentMonth.getFullYear()}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setCurrentMonth(
                isRTL ? subMonths(currentMonth, 1) : addMonths(currentMonth, 1)
              )
            }
            className="p-2"
          >
            <ChevronRight className="w-4 h-4 text-black" />
          </Button>
        </div>

        {/* Days of Week Header */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {t.days.map((day, index) => (
            <div
              key={`${day}-${index}`}
              className="text-center text-sm text-gray-500 py-2 font-medium"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-1 mb-6">
          {emptyCells.map((_, index) => (
            <div key={`empty-${index}`} className="h-10" />
          ))}

          {daysInMonth.map((date: Date) => {
            const isSelected =
              tempSelectedDate && isSameDay(date, tempSelectedDate);
            const isTodayDate = isToday(date);
            const isPastDate = date < startOfDay(today);

            return (
              <button
                key={date.toISOString()}
                onClick={() => !isPastDate && handleDateClick(date)}
                disabled={isPastDate}
                className={cn(
                  "h-10 w-10 rounded-full text-sm font-medium transition-colors",
                  "hover:bg-gray-200 focus:outline-none text-black focus:ring-2 focus:ring-yellow-400",
                  {
                    "bg-yellow-400 text-black": isSelected,
                    "ring-2 ring-yellow-400": isTodayDate && !isSelected,
                    "text-gray-900": !isSelected && !isTodayDate,
                    "opacity-40 cursor-not-allowed": isPastDate,
                  }
                )}
              >
                {format(date, "d")}
              </button>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div
          className={cn("flex justify-between text-black", isRTL && "flex-row-reverse")}
        >
          <Button
            variant="ghost"
            onClick={onClose}
            className=" hover:text-gray-800"
          >
            {t.close}
          </Button>

          <div dir="ltr" className="flex gap-2">
            <Button
              variant="ghost"
              onClick={handleCancel}
              className=" hover:text-gray-800"
            >
              {t.cancel}
            </Button>
            <Button
              onClick={handleOK}
              className="bg-gray-800 text-white hover:bg-gray-900 px-6"
            >
              {t.ok}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
