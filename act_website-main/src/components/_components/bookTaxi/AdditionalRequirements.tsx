"use client";
import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, ClipboardList } from "lucide-react";
import { Locale } from "../../../../i18n.config";
import { AdditionalRequirementsForm } from ".";

type Props = {
  locale: Locale;
  additionalRequirements: AdditionalRequirementsForm;
  setAdditionalRequirements: (details: AdditionalRequirementsForm) => void;
  nextStep: () => void;
  prevStep: () => void;
};

export default function AdditionalRequirements({
  locale,
  additionalRequirements,
  setAdditionalRequirements,
  nextStep,
  prevStep,
}: Props) {
  const isRTL = locale === "ar";

  return (
    <div className="w-full max-w-3xl max-xl:mx-auto" dir={isRTL ? "rtl" : "ltr"}>
      <div className="mb-6">
        <Button
          onClick={prevStep}
          variant="outline"
          size="lg"
          className="bg-white/10 backdrop-blur-sm border-white/20 text-white hover:bg-white/20 hover:border-white/30 transition-all duration-300 cursor-pointer hover:text-white"
        >
          <ChevronLeft className={`w-5 h-5 ${isRTL ? "rotate-180 ml-2" : "mr-2"}`} />
          Back
        </Button>
      </div>

      <Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-xl sm:text-2xl">
            <ClipboardList className="w-5 h-5 text-[#ffd100]" />
            Additional Requirements
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center gap-3 rounded-lg border border-white/20 bg-white/5 p-3 text-white cursor-pointer hover:bg-white/10">
            <input
              type="checkbox"
              checked={additionalRequirements.meetAndGreet}
              onChange={(event) =>
                setAdditionalRequirements({
                  ...additionalRequirements,
                  meetAndGreet: event.target.checked,
                })
              }
            />
            <span>Meet & Greet</span>
          </label>
          <label className="flex items-center gap-3 rounded-lg border border-white/20 bg-white/5 p-3 text-white cursor-pointer hover:bg-white/10">
            <input
              type="checkbox"
              checked={additionalRequirements.foldableWheelchair}
              onChange={(event) =>
                setAdditionalRequirements({
                  ...additionalRequirements,
                  foldableWheelchair: event.target.checked,
                })
              }
            />
            <span>Foldable Wheelchair</span>
          </label>
          <div>
            <label htmlFor="notes-to-driver">
              <p className="text-white">Notes to Driver</p>
            </label>
            <textarea
              id="notes-to-driver"
              value={additionalRequirements.notesToDriver}
              onChange={(event) =>
                setAdditionalRequirements({
                  ...additionalRequirements,
                  notesToDriver: event.target.value,
                })
              }
              rows={5}
              className="w-full p-2.5 mb-2 border-2 bg-white text-foreground font-semibold border-muted rounded-lg resize-none"
            />
          </div>
          <Button
            type="button"
            onClick={nextStep}
            className="w-full bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold py-6 text-base sm:text-lg shadow-xl cursor-pointer"
          >
            Continue
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
