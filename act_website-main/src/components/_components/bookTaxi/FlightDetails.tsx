"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, Plane } from "lucide-react";
import { Locale } from "../../../../i18n.config";
import { FlightDetailsForm } from ".";

type Props = {
  locale: Locale;
  flightDetails: FlightDetailsForm;
  setFlightDetails: (details: FlightDetailsForm) => void;
  nextStep: () => void;
  prevStep: () => void;
};

export default function FlightDetails({
  locale,
  flightDetails,
  setFlightDetails,
  nextStep,
  prevStep,
}: Props) {
  const isRTL = locale === "ar";
  const [isRequired, setIsRequired] = useState(false);
  const inputClass =
    "w-full p-2.5 mb-2 border-2 bg-white text-foreground font-semibold border-muted rounded-lg";
  const optionClass =
    "flex items-center gap-3 rounded-lg border border-white/20 bg-white/5 p-3 text-white cursor-pointer hover:bg-white/10";

  const updateField = (key: keyof FlightDetailsForm, value: string) => {
    setFlightDetails({ ...flightDetails, [key]: value });
  };

  const onSubmit = () => {
    const missingArrivalTime =
      flightDetails.flightType === "arrival" && !flightDetails.landingTime.trim();
    const missingDepartureTime =
      flightDetails.flightType === "departure" && !flightDetails.departureTime.trim();

    if (missingArrivalTime || missingDepartureTime) {
      setIsRequired(true);
      return;
    }

    nextStep();
  };

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
            <Plane className="w-5 h-5 text-[#ffd100]" />
            Flight Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <p className="text-white">Flight Type</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <label className={optionClass}>
                <input
                  type="radio"
                  name="flight-type"
                  checked={flightDetails.flightType === "arrival"}
                  onChange={() => updateField("flightType", "arrival")}
                />
                <span>Arrival</span>
              </label>
              <label className={optionClass}>
                <input
                  type="radio"
                  name="flight-type"
                  checked={flightDetails.flightType === "departure"}
                  onChange={() => updateField("flightType", "departure")}
                />
                <span>Departure</span>
              </label>
            </div>
            <p className="text-xs text-white/60">
              Flight type is optional. Select one if you would like to add flight timing details.
            </p>
          </div>

          {flightDetails.flightType && (
            <>
          <div>
            <label htmlFor="flight-number">
              <p className="text-white">Flight Number</p>
            </label>
            <input
              id="flight-number"
              value={flightDetails.flightNumber}
              onChange={(event) => updateField("flightNumber", event.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="airline">
              <p className="text-white">Airline</p>
            </label>
            <input
              id="airline"
              value={flightDetails.airline}
              onChange={(event) => updateField("airline", event.target.value)}
              className={inputClass}
            />
          </div>
          {flightDetails.flightType === "arrival" && (
            <div>
              <label htmlFor="landing-time">
                <p className="text-white">Landing Time</p>
              </label>
              <input
                id="landing-time"
                value={flightDetails.landingTime}
                onChange={(event) => updateField("landingTime", event.target.value)}
                className={inputClass}
              />
            </div>
          )}
          {flightDetails.flightType === "departure" && (
            <div>
              <label htmlFor="departure-time">
                <p className="text-white">Departure Time</p>
              </label>
              <input
                id="departure-time"
                value={flightDetails.departureTime}
                onChange={(event) => updateField("departureTime", event.target.value)}
                className={inputClass}
              />
            </div>
          )}
          <div>
            <label htmlFor="pickup-sign-name">
              <p className="text-white">Pick-up Sign Name</p>
            </label>
            <input
              id="pickup-sign-name"
              value={flightDetails.pickupSignName}
              onChange={(event) => updateField("pickupSignName", event.target.value)}
              className={inputClass}
            />
          </div>
            </>
          )}

          {isRequired && (
            <p className="text-red-300 text-sm font-semibold">
              {flightDetails.flightType === "departure"
                ? "Departure Time is required for departure flights."
                : "Landing Time is required for arrival flights."}
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
