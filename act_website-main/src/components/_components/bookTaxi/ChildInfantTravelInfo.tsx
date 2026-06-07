"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, Baby } from "lucide-react";
import { Locale } from "../../../../i18n.config";
import { ChildInfantTravelForm, PassengerCounts } from ".";

type Props = {
  locale: Locale;
  passengerCounts: PassengerCounts;
  childInfantTravel: ChildInfantTravelForm;
  setChildInfantTravel: (details: ChildInfantTravelForm) => void;
  nextStep: () => void;
  prevStep: () => void;
};

const infantOptions = [
  "I will provide my own infant seats",
  "I would like ACT to provide infant seats",
  "I understand ACT may not have infant seats available and wish to continue",
];

const childOptions = [
  "I will provide my own child seats",
  "I would like ACT to provide child seats",
  "I understand ACT may not have child seats available and wish to continue",
];

export default function ChildInfantTravelInfo({
  locale,
  passengerCounts,
  childInfantTravel,
  setChildInfantTravel,
  nextStep,
  prevStep,
}: Props) {
  const isRTL = locale === "ar";
  const [isRequired, setIsRequired] = useState(false);

  const onSubmit = () => {
    const missingInfantOption = passengerCounts.infants > 0 && !childInfantTravel.infantSeatOption;
    const missingChildOption = passengerCounts.children > 0 && !childInfantTravel.childSeatOption;

    if (missingInfantOption || missingChildOption) {
      setIsRequired(true);
      return;
    }

    nextStep();
  };

  const optionClass =
    "flex items-start gap-3 rounded-lg border border-white/20 bg-white/5 p-3 text-white cursor-pointer hover:bg-white/10";

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
            <Baby className="w-5 h-5 text-[#ffd100]" />
            Travelling with Children or Infants?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm sm:text-base text-white/80">
            UK guidance generally requires children to use an appropriate child restraint based on age, height and weight. Please confirm how child or infant seats will be handled for this booking.
          </p>

          {passengerCounts.infants > 0 && (
            <div className="space-y-3">
              <h3 className="text-white font-bold">Infant Seat Requirement</h3>
              {infantOptions.map((option) => (
                <label key={option} className={optionClass}>
                  <input
                    type="radio"
                    name="infant-seat-option"
                    value={option}
                    checked={childInfantTravel.infantSeatOption === option}
                    onChange={() =>
                      setChildInfantTravel({ ...childInfantTravel, infantSeatOption: option })
                    }
                    className="mt-1"
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
          )}

          {passengerCounts.children > 0 && (
            <div className="space-y-3">
              <h3 className="text-white font-bold">Child Seat Requirement</h3>
              {childOptions.map((option) => (
                <label key={option} className={optionClass}>
                  <input
                    type="radio"
                    name="child-seat-option"
                    value={option}
                    checked={childInfantTravel.childSeatOption === option}
                    onChange={() =>
                      setChildInfantTravel({ ...childInfantTravel, childSeatOption: option })
                    }
                    className="mt-1"
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
          )}

          <details className="rounded-lg border border-white/20 bg-white/5 p-4 text-white">
            <summary className="cursor-pointer text-sm font-semibold text-[#ffd100]">
              Read UK guidance
            </summary>
            <ul className="mt-3 space-y-2 text-sm text-white/80">
              <li>• Infants (0-3 years): Should travel in a suitable infant or child seat.</li>
              <li>• Children (4-11 years): Should normally use a suitable child seat until 12 years old or 135cm tall, whichever comes first.</li>
              <li>• Children aged 12+ or taller than 135cm: Must use an adult seat belt.</li>
            </ul>
          </details>

          {isRequired && (
            <p className="text-red-300 text-sm font-semibold">
              Please select the required child or infant seat option before continuing.
            </p>
          )}

          <Button
            type="button"
            onClick={onSubmit}
            className="w-full bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold py-6 text-base sm:text-lg shadow-xl cursor-pointer"
          >
            Continue
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
