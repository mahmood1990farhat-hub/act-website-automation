"use client";
import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, ClipboardList } from "lucide-react";
import { Locale } from "../../../../i18n.config";
import { AdditionalInformation, AdditionalRequirementsForm } from ".";

type Props = {
  locale: Locale;
  translations: AdditionalInformation;
  additionalRequirements: AdditionalRequirementsForm;
  setAdditionalRequirements: (details: AdditionalRequirementsForm) => void;
  nextStep: () => void;
  prevStep: () => void;
};

export default function AdditionalRequirements({
  locale,
  translations,
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
          {translations.back}
        </Button>
      </div>

      <Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-xl sm:text-2xl">
            <ClipboardList className="w-5 h-5 text-[#ffd100]" />
            {translations.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <label htmlFor="notes-to-driver" className="block text-white font-semibold">
              {translations.driverTitle}
            </label>
            <p className="mt-2 text-sm leading-6 text-white/75">
              {translations.description}
            </p>
            <textarea
              id="notes-to-driver"
              value={additionalRequirements.notesToDriver}
              onChange={(event) =>
                setAdditionalRequirements({
                  notesToDriver: event.target.value,
                })
              }
              rows={7}
              className="mt-4 w-full min-h-44 resize-y rounded-lg border-2 border-muted bg-white p-3 font-semibold text-foreground"
            />
          </div>
          <Button
            type="button"
            onClick={nextStep}
            className="w-full bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold py-6 text-base sm:text-lg shadow-xl cursor-pointer"
          >
            {translations.continue}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
