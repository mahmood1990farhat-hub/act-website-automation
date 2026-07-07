"use client";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, Plane } from "lucide-react";
import { Locale } from "../../../../i18n.config";
import { FlightDetailsForm, RoutePoint } from ".";
import { TimeInput } from "../dateAndTime/time-input";
import {
  getAirportJourneyDirection,
  getArrivalGuidance,
  getDepartureGuidance,
} from "./flight-guidance";

type Props = {
  locale: Locale;
  flightDetails: FlightDetailsForm;
  setFlightDetails: (details: FlightDetailsForm) => void;
  nextStep: () => void;
  prevStep: () => void;
  pickupTime: string;
  routePoints: RoutePoint[];
  changePickupTime: () => void;
};

type TimeValue = {
  hour: number;
  minute: number;
};

const parseTimeValue = (time: string): TimeValue | undefined => {
  const match = time.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return undefined;

  const hour = Number(match[1]);
  const minute = Number(match[2]);

  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return undefined;

  return { hour, minute };
};

export default function FlightDetails({
  locale,
  flightDetails,
  setFlightDetails,
  nextStep,
  prevStep,
  pickupTime,
  routePoints,
  changePickupTime,
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

  const journeyDirection = getAirportJourneyDirection(routePoints);
  const isDirectionDetected = journeyDirection !== "manual";
  const timingWarning =
    flightDetails.flightType === "arrival"
      ? getArrivalGuidance(pickupTime, flightDetails.landingTime)
      : flightDetails.flightType === "departure"
        ? getDepartureGuidance(pickupTime, flightDetails.departureTime)
        : "";

  useEffect(() => {
    if (!isDirectionDetected || flightDetails.flightType === journeyDirection) return;

    setFlightDetails({
      ...flightDetails,
      flightType: journeyDirection,
      landingTime: journeyDirection === "arrival" ? flightDetails.landingTime : "",
      departureTime:
        journeyDirection === "departure" ? flightDetails.departureTime : "",
    });
  }, [flightDetails, isDirectionDetected, journeyDirection, setFlightDetails]);

  const skipFlightDetails = () => {
    setFlightDetails({
      flightType: "",
      flightNumber: "",
      airline: "",
      landingTime: "",
      departureTime: "",
      pickupSignName: "",
    });
    setIsRequired(false);
    nextStep();
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
            <div
              className={`grid grid-cols-1 ${isDirectionDetected ? "" : "sm:grid-cols-2"} gap-2`}
            >
              {journeyDirection !== "departure" && (
              <label className={optionClass}>
                <input
                  type="radio"
                  name="flight-type"
                  checked={flightDetails.flightType === "arrival"}
                  onChange={() => updateField("flightType", "arrival")}
                />
                <span>Arrival</span>
              </label>
              )}
              {journeyDirection !== "arrival" && (
              <label className={optionClass}>
                <input
                  type="radio"
                  name="flight-type"
                  checked={flightDetails.flightType === "departure"}
                  onChange={() => updateField("flightType", "departure")}
                />
                <span>Departure</span>
              </label>
              )}
            </div>
            <p className="text-xs text-white/60">
              {journeyDirection === "arrival"
                ? "Arrival is selected because your journey starts at an airport."
                : journeyDirection === "departure"
                  ? "Departure is selected because your journey ends at an airport."
                  : "Flight type is optional. Select one if you would like to add flight timing details."}
            </p>
          </div>

          {flightDetails.flightType && (
            <>
          <div className="rounded-lg border border-[#ffd100]/30 bg-[#ffd100]/10 p-3">
            <p className="text-[#ffd100] text-sm font-semibold">
              Please enter the scheduled flight landing/departure time.
            </p>
            <p className="text-white/70 text-xs mt-1">
              {flightDetails.flightType === "arrival"
                ? "For arrivals, your pickup time should allow enough time for immigration, baggage collection, and meeting your driver."
                : "For departures, allow enough travel and airport check-in time before your scheduled flight."}
            </p>
          </div>
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
              <TimeInput
                id="landing-time"
                value={parseTimeValue(flightDetails.landingTime)}
                language={locale}
                required={isRequired}
                placeholder="Select landing time"
                setFormattedTime={(time) => updateField("landingTime", time)}
                className="border-muted"
              />
            </div>
          )}
          {flightDetails.flightType === "departure" && (
            <div>
              <label htmlFor="departure-time">
                <p className="text-white">Departure Time</p>
              </label>
              <TimeInput
                id="departure-time"
                value={parseTimeValue(flightDetails.departureTime)}
                language={locale}
                required={isRequired}
                placeholder="Select departure time"
                setFormattedTime={(time) => updateField("departureTime", time)}
                className="border-muted"
              />
            </div>
          )}
          {timingWarning && (
            <div className="rounded-lg border border-[#ffd100]/60 bg-black/30 p-4 text-sm text-white shadow-lg">
              <p className="font-semibold leading-relaxed">{timingWarning}</p>
              <Button
                type="button"
                variant="link"
                onClick={changePickupTime}
                className="mt-2 h-auto p-0 font-bold text-[#ffd100] hover:text-[#ffd100]/80"
              >
                Go back and change pickup time
              </Button>
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
          <Button
            type="button"
            onClick={skipFlightDetails}
            variant="outline"
            className="w-full border border-white/20 bg-white/10 text-white hover:bg-white/20 hover:text-white font-semibold py-6 text-base sm:text-lg cursor-pointer"
          >
            Skip — Not applicable for this journey
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
