"use client";

import { useEffect, useRef, useState } from "react";
import { Clock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const translations = {
  ar: {
    selectTime: "اختر الوقت",
    cancel: "إلغاء",
    ok: "موافق",
    hour: "الساعة",
    minute: "الدقيقة",
    period: "الفترة",
  },
  en: {
    selectTime: "Select time",
    cancel: "Cancel",
    ok: "OK",
    hour: "Hour",
    minute: "Minute",
    period: "AM/PM",
  },
};

type Language = "ar" | "en";
type Period = "AM" | "PM";

interface TimeValue {
  hour: number;
  minute: number;
}

interface DisplayTimeValue {
  hour: number;
  minute: number;
  period: Period;
}

interface ActTimePickerProps {
  isOpen?: boolean;
  onClose: () => void;
  onSelect: (time: TimeValue) => void;
  selectedTime?: TimeValue;
  onCancel?: () => void;
  language?: Language;
  inCreateCaptain?: true;
}

type WheelOption = {
  label: string;
  value: number | Period;
};

const ROW_HEIGHT = 48;

const toDisplayTime = (time?: TimeValue): DisplayTimeValue => {
  const now = new Date();
  const hour24 = time?.hour ?? now.getHours();

  return {
    hour: hour24 % 12 || 12,
    minute: time?.minute ?? now.getMinutes(),
    period: hour24 >= 12 ? "PM" : "AM",
  };
};

const toStoredTime = (time: DisplayTimeValue): TimeValue => {
  const hour =
    time.period === "AM"
      ? time.hour % 12
      : time.hour === 12
        ? 12
        : time.hour + 12;

  return { hour, minute: time.minute };
};

function WheelColumn({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: WheelOption[];
  value: number | Period;
  onChange: (value: number | Period) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const selectedIndex = Math.max(
    options.findIndex((option) => option.value === value),
    0
  );

  useEffect(() => {
    containerRef.current?.scrollTo({
      top: selectedIndex * ROW_HEIGHT,
      behavior: "auto",
    });
  }, [selectedIndex]);

  useEffect(
    () => () => {
      if (scrollTimer.current) clearTimeout(scrollTimer.current);
    },
    []
  );

  const handleScroll = () => {
    if (scrollTimer.current) clearTimeout(scrollTimer.current);

    scrollTimer.current = setTimeout(() => {
      const container = containerRef.current;
      if (!container) return;

      const index = Math.min(
        Math.max(Math.round(container.scrollTop / ROW_HEIGHT), 0),
        options.length - 1
      );
      onChange(options[index].value);
      container.scrollTo({ top: index * ROW_HEIGHT, behavior: "smooth" });
    }, 80);
  };

  return (
    <div className="min-w-0 flex-1 text-center">
      <p className="mb-2 text-xs font-semibold uppercase text-white/60">{label}</p>
      <div className="relative overflow-hidden rounded-lg border border-white/15 bg-black/25">
        <div className="pointer-events-none absolute inset-x-1 top-1/2 z-10 h-12 -translate-y-1/2 rounded-md border border-[#ffd100]/60 bg-[#ffd100]/15" />
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="h-48 snap-y snap-mandatory overflow-y-auto overscroll-contain py-[72px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {options.map((option) => {
            const isSelected = option.value === value;

            return (
              <button
                key={String(option.value)}
                type="button"
                onClick={() => onChange(option.value)}
                className={cn(
                  "relative z-20 flex h-12 w-full snap-center items-center justify-center text-base transition-all",
                  isSelected
                    ? "font-bold text-[#ffd100]"
                    : "font-medium text-white/45"
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function ActTimePicker({
  isOpen,
  onClose,
  onSelect,
  selectedTime,
  onCancel,
  language = "ar",
  inCreateCaptain,
}: ActTimePickerProps) {
  const [tempTime, setTempTime] = useState<DisplayTimeValue>(() =>
    toDisplayTime(selectedTime)
  );

  useEffect(() => {
    if (isOpen) setTempTime(toDisplayTime(selectedTime));
  }, [isOpen, selectedTime]);

  useEffect(() => {
    if (!isOpen || inCreateCaptain) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [inCreateCaptain, isOpen]);

  if (!isOpen) return null;

  const t = translations[language];
  const isRTL = language === "ar";
  const hourOptions: WheelOption[] = Array.from({ length: 12 }, (_, index) => ({
    label: String(index + 1).padStart(2, "0"),
    value: index + 1,
  }));
  const minuteOptions: WheelOption[] = Array.from({ length: 60 }, (_, minute) => ({
    label: String(minute).padStart(2, "0"),
    value: minute,
  }));
  const periodOptions: WheelOption[] = [
    { label: "AM", value: "AM" },
    { label: "PM", value: "PM" },
  ];

  const handleOK = () => {
    onSelect(toStoredTime(tempTime));
    onClose();
  };

  const handleCancel = () => {
    setTempTime(toDisplayTime(selectedTime));
    onCancel?.();
    onClose();
  };

  const displayTime = `${tempTime.hour}:${String(tempTime.minute).padStart(2, "0")} ${tempTime.period}`;

  const pickerContent = (
    <div
      role="dialog"
      aria-modal={!inCreateCaptain}
      aria-label={t.selectTime}
      onClick={(event) => event.stopPropagation()}
      className="w-full max-w-md rounded-t-2xl border border-white/20 bg-[#1f2020] p-4 pb-[max(1rem,env(safe-area-inset-bottom))] text-white shadow-2xl sm:rounded-xl sm:p-5"
      dir={isRTL ? "rtl" : "ltr"}
    >
      <div className="mb-4 flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-3">
        <div>
          <p className="mb-1 text-sm text-white/65">{t.selectTime}</p>
          <p className="text-2xl font-bold text-[#ffd100]">{displayTime}</p>
        </div>
        <Clock className="h-6 w-6 text-[#ffd100]" />
      </div>

      <div className="mb-5 flex gap-2 sm:gap-3">
        <WheelColumn
          label={t.hour}
          options={hourOptions}
          value={tempTime.hour}
          onChange={(hour) =>
            setTempTime((current) => ({ ...current, hour: Number(hour) }))
          }
        />
        <WheelColumn
          label={t.minute}
          options={minuteOptions}
          value={tempTime.minute}
          onChange={(minute) =>
            setTempTime((current) => ({ ...current, minute: Number(minute) }))
          }
        />
        <WheelColumn
          label={t.period}
          options={periodOptions}
          value={tempTime.period}
          onChange={(period) =>
            setTempTime((current) => ({ ...current, period: period as Period }))
          }
        />
      </div>

      <div className="grid grid-cols-2 gap-3" dir="ltr">
        <Button
          variant="outline"
          onClick={handleCancel}
          className="h-12 border-white/20 bg-white/5 text-white hover:bg-white/10 hover:text-white"
          type="button"
        >
          {t.cancel}
        </Button>
        <Button
          onClick={handleOK}
          className="h-12 bg-[#ffd100] font-bold text-[#2D2E2E] hover:bg-[#ffd100]/90"
          type="button"
        >
          {t.ok}
        </Button>
      </div>
    </div>
  );

  return inCreateCaptain ? (
    pickerContent
  ) : (
    <div
      onClick={handleCancel}
      className="fixed inset-0 z-[100] flex items-end bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:justify-center sm:p-4"
    >
      {pickerContent}
    </div>
  );
}
