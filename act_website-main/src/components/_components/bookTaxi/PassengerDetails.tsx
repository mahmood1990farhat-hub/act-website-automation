"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, User } from "lucide-react";
import { Locale } from "../../../../i18n.config";
import { PassengerDetailsForm } from ".";

type Props = {
  locale: Locale;
  passengerDetails: PassengerDetailsForm;
  setPassengerDetails: (details: PassengerDetailsForm) => void;
  nextStep: () => void;
  prevStep: () => void;
};

export default function PassengerDetails({
  locale,
  passengerDetails,
  setPassengerDetails,
  nextStep,
  prevStep,
}: Props) {
  const isRTL = locale === "ar";
  const [isRequired, setIsRequired] = useState(false);

  const updateField = (key: keyof PassengerDetailsForm, value: string) => {
    setPassengerDetails({ ...passengerDetails, [key]: value });
  };

  const onSubmit = () => {
    const hasRequiredDetails =
      passengerDetails.fullName.trim() &&
      passengerDetails.email.trim() &&
      passengerDetails.countryCode.trim() &&
      passengerDetails.mobileNumber.trim();

    if (!hasRequiredDetails) {
      setIsRequired(true);
      return;
    }

    nextStep();
  };

  const inputClass =
    "w-full p-2.5 mb-2 border-2 bg-white text-foreground font-semibold border-muted rounded-lg";

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
          {isRTL ? "Back" : "Back"}
        </Button>
      </div>

      <Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-xl sm:text-2xl">
            <User className="w-5 h-5 text-[#ffd100]" />
            Passenger Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label htmlFor="passenger-full-name">
              <p className="text-white">Full Name</p>
            </label>
            <input
              id="passenger-full-name"
              value={passengerDetails.fullName}
              onChange={(event) => updateField("fullName", event.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="passenger-email">
              <p className="text-white">Email</p>
            </label>
            <input
              id="passenger-email"
              type="email"
              value={passengerDetails.email}
              onChange={(event) => updateField("email", event.target.value)}
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-[220px_1fr] gap-4">
            <div>
              <label htmlFor="passenger-country-code">
                <p className="text-white">Country Code</p>
              </label>
              <select
                id="passenger-country-code"
                value={passengerDetails.countryCode}
                onChange={(event) => updateField("countryCode", event.target.value)}
                className={inputClass}
              >
                <option value="+44 United Kingdom">+44 United Kingdom</option>
                <option value="+1 United States">+1 United States</option>
                <option value="+971 United Arab Emirates">+971 United Arab Emirates</option>
                <option value="+966 Saudi Arabia">+966 Saudi Arabia</option>
                <option value="+974 Qatar">+974 Qatar</option>
                <option value="+965 Kuwait">+965 Kuwait</option>
                <option value="+973 Bahrain">+973 Bahrain</option>
                <option value="+968 Oman">+968 Oman</option>
              </select>
            </div>
            <div>
            <label htmlFor="passenger-mobile">
              <p className="text-white">Mobile Number</p>
            </label>
            <input
              id="passenger-mobile"
              type="tel"
              value={passengerDetails.mobileNumber}
              onChange={(event) => updateField("mobileNumber", event.target.value)}
              className={inputClass}
            />
            </div>
          </div>

          {isRequired && (
            <p className="text-red-300 text-sm font-semibold">
              Passenger name, email, country code, and mobile number are required.
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
