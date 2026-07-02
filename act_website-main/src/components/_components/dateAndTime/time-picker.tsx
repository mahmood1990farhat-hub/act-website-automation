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
      className="w-full max-w-sm mx-auto rounded-xl border border-white/20 bg-[#1f2020] p-5 text-white shadow-2xl"
      dir={isRTL ? "rtl" : "ltr"}
    >
      {/* Header */}
      <div className="mb-5 rounded-lg border border-white/10 bg-white/5 p-4">
        <h2 className="text-sm text-white/70 mb-2">{t.selectTime}</h2>
        <div className="flex items-center justify-between">
          <div className="text-3xl font-bold tracking-wide text-[#ffd100]">
            {formatTime(tempTime)}
          </div>
          <Clock className="w-5 h-5 text-[#ffd100]" />
        </div>
      </div>

      {/* Pickers */}
      <div className="flex items-start justify-center gap-4 mb-6">
        {/* Hours */}
        <div className="flex flex-col items-center">
          <div className="text-xs font-semibold uppercase tracking-wide text-white/60 mb-2">
            {t.hour}
          </div>
          <div className="flex flex-col items-center max-h-60 overflow-y-auto on-scrollbar rounded-lg border border-white/10 bg-black/20 p-2">
            <div className="grid grid-cols-3 gap-2">
              {hours.map((h, idx) => (
                <button
                  key={h}
                  ref={(el) => {
                    if (el) hourRefs.current[idx] = el;
                  }}
                  className={cn(
                    "h-10 w-12 rounded-md text-center text-sm font-semibold transition-colors",
                    tempTime.hour === h
                      ? "bg-[#ffd100] text-[#2D2E2E] shadow"
                      : "bg-white/10 text-white hover:bg-white/20"
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
          <div className="text-xs font-semibold uppercase tracking-wide text-white/60 mb-2">
            {t.minute}
          </div>
          <div className="max-h-60 overflow-y-auto on-scrollbar rounded-lg border border-white/10 bg-black/20 p-2">
            <div className="grid grid-cols-3 gap-2">
              {minutes.map((m, idx) => (
                <button
                  key={m}
                  ref={(el) => {
                    if (el) minuteRefs.current[idx] = el;
                  }}
                  className={cn(
                    "h-10 w-12 rounded-md text-center text-sm font-semibold transition-colors",
                    tempTime.minute === m
                      ? "bg-[#ffd100] text-[#2D2E2E] shadow"
                      : "bg-white/10 text-white hover:bg-white/20"
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
          className="text-white/70 hover:bg-white/10 hover:text-white"
          type="button"
        >
          {t.close}
        </Button>

        <div dir="ltr" className="flex gap-2">
          <Button
            variant="ghost"
            onClick={handleCancel}
            className="text-white/70 hover:bg-white/10 hover:text-white"
            type="button"
          >
            {t.cancel}
          </Button>
          <Button
            onClick={handleOK}
            className="bg-[#ffd100] text-[#2D2E2E] hover:bg-[#ffd100]/90 px-6 font-bold"
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
