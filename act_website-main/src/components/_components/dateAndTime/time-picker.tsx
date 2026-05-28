"use client";

import { useState, useEffect, useRef } from "react";
import { Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const translations = {
  ar: {
    selectTime: "اختر الوقت",
    close: "إغلاق",
    cancel: "إلغاء",
    ok: "موافق",
    hour: "الساعة",
    minute: "الدقيقة",

  },
  en: {
    selectTime: "Select time",
    close: "Close",
    cancel: "Cancel",
    ok: "OK",
    hour: "Hour",
    minute: "Minute",
  },
};

type Language = "ar" | "en";

interface TimeValue {
  hour: number;
  minute: number;
}

interface MobileTimePickerProps {
  isOpen?: boolean;
  onClose: () => void;
  onSelect: (time: TimeValue) => void;
  selectedTime?: TimeValue;
  onCancel?: () => void;
  language?: Language;
  inCreateCaptain?: true;
}

export function TimePicker({
  isOpen,
  onClose,
  onSelect,
  selectedTime,
  onCancel,
  language = "ar",
  inCreateCaptain,
}: MobileTimePickerProps) {
  const initialTime: TimeValue = selectedTime
    ? { ...selectedTime }
    : { hour: 0, minute: 0 };

  const [tempTime, setTempTime] = useState<TimeValue>(initialTime);

  const hourRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const minuteRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    const hourIndex = tempTime.hour;
    const minuteIndex = tempTime.minute;

    const hourBtn = hourRefs.current[hourIndex];
    const minuteBtn = minuteRefs.current[minuteIndex];

    hourBtn?.scrollIntoView({ behavior: "smooth", block: "center" });
    minuteBtn?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [tempTime.hour, tempTime.minute]);

  if (!isOpen) return null;

  const t = translations[language];
  const isRTL = language === "ar";

  const hours = Array.from({ length: 24 }, (_, i) => i);
  const minutes = Array.from({ length: 60 }, (_, i) => i);

  const handleTimeChange = (field: keyof TimeValue, value: number) => {
    setTempTime((prev) => ({ ...prev, [field]: value }));
  };

  const handleOK = () => {
    onSelect(tempTime);
    onClose();
  };

  const handleCancel = () => {
    setTempTime(selectedTime ? { ...selectedTime } : { hour: 0, minute: 0 });
    onCancel?.();
    onClose();
  };

  const formatTime = (time: TimeValue) => {
    return `${time.hour.toString().padStart(2, "0")}:${time.minute
      .toString()
      .padStart(2, "0")}`;
  };

  const TimePickerContent = (
    <div
      onClick={(e) => e.stopPropagation()}
      className="bg-gray-100 rounded-3xl p-6 text-black w-full max-w-sm mx-auto"
      dir={isRTL ? "rtl" : "ltr"}
    >
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-sm text-gray-600 mb-3">{t.selectTime}</h2>
        <div className="flex items-center justify-between">
          <div className="text-2xl font-medium text-gray-900">
            {formatTime(tempTime)}
          </div>
          <Clock className="w-5 h-5 text-gray-500" />
        </div>
      </div>

      {/* Pickers */}
      <div className="flex items-start justify-center gap-4 mb-8">
        {/* Hours */}
        <div className="flex flex-col items-center">
          <div className="text-xs text-gray-500 mb-1">{t.hour}</div>
          <div className="flex flex-col items-center max-h-60 overflow-y-auto on-scrollbar">
            <div className="grid grid-rows-6 gap-2">
              {hours.map((h, idx) => (
                <button
                  key={h}
                  ref={(el) => {
                    if (el) hourRefs.current[idx] = el;
                  }}
                  className={cn(
                    "p-2.5 rounded-md text-center",
                    tempTime.hour === h
                      ? "bg-primary"
                      : "bg-white text-black",
                    "hover:bg-gray-300"
                  )}
                  onClick={() => handleTimeChange("hour", h)}
                  type="button"
                >
                  {h.toString().padStart(2, "0")}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Minutes */}
        <div className="flex flex-col items-center">
          <div className="text-xs text-gray-500 mb-1">{t.minute}</div>
          <div className="max-h-60 overflow-y-auto on-scrollbar">
            <div className="grid grid-rows-6 gap-2">
              {minutes.map((m, idx) => (
                <button
                  key={m}
                  ref={(el) => {
                    if (el) minuteRefs.current[idx] = el;
                  }}
                  className={cn(
                    "p-2.5 rounded-md text-center",
                    tempTime.minute === m
                      ? "bg-primary"
                      : "bg-white text-black",
                    "hover:bg-gray-300"
                  )}
                  onClick={() => handleTimeChange("minute", m)}
                  type="button"
                >
                  {m.toString().padStart(2, "0")}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className={cn("flex justify-between", isRTL && "flex-row-reverse")}>
        <Button
          variant="ghost"
          onClick={onClose}
          className="text-muted-foreground hover:text-gray-800"
          type="button"
        >
          {t.close}
        </Button>

        <div dir="ltr" className="flex gap-2">
          <Button
            variant="ghost"
            onClick={handleCancel}
            className="text-muted-foreground hover:text-gray-800"
            type="button"
          >
            {t.cancel}
          </Button>
          <Button
            onClick={handleOK}
            className="bg-gray-800 text-white hover:bg-gray-900 px-6"
            type="button"
          >
            {t.ok}
          </Button>
        </div>
      </div>
    </div>
  );

  return inCreateCaptain ? (
    TimePickerContent
  ) : (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
    >
      {TimePickerContent}
    </div>
  );
}
