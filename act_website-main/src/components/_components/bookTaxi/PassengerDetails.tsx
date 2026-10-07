"use client";
import { customerText } from "@/lib/customer-text";
import { bookingText } from "./booking-text";
import React, { useState } from "react";
import { getCountries, getCountryCallingCode, isValidPhoneNumber } from "react-phone-number-input";
import enCountries from "react-phone-number-input/locale/en.json";
import { customerPhoneLabels } from "@/lib/customer-phone-labels";
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
  const countryLabels = customerPhoneLabels(locale);
  const isRTL = locale === "ar";
  const t = (text: string) => bookingText(locale, text);
  const [validationError, setValidationError] = useState("");

  const updateField = (key: keyof PassengerDetailsForm, value: string) => {
    setPassengerDetails({ ...passengerDetails, [key]: value });
  };

  const onSubmit = () => {
    const fullName = passengerDetails.fullName.trim();
    const email = passengerDetails.email.trim();
    const countryCode = passengerDetails.countryCode.trim();
    const mobileNumber = passengerDetails.mobileNumber.trim();

    if (!fullName || !email || !countryCode || !mobileNumber) {
      setValidationError(t("Passenger name, email, country code, and mobile number are required."));
      return;
    }

    const emailLooksValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    if (!emailLooksValid) {
      setValidationError(t("Enter a valid email address."));
      return;
    }

    const dialCode = countryCode.match(/^\+\d+/)?.[0] ?? "";
    const enteredDigits = mobileNumber.replace(/[^\d+]/g, "");
    const internationalPhone = enteredDigits.startsWith("+")
      ? enteredDigits
      : `${dialCode}${enteredDigits.replace(/^0+/, "")}`;

    if (!dialCode || !internationalPhone.startsWith(dialCode) || !isValidPhoneNumber(internationalPhone)) {
      setValidationError(t("Enter a valid mobile number for the selected country code."));
      return;
    }

    // The backend stores/displays the country code and national number separately.
    setPassengerDetails({
      ...passengerDetails,
      fullName,
      email,
      countryCode,
      mobileNumber: internationalPhone.slice(dialCode.length),
    });
    setValidationError("");
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
          {isRTL ? t("Back") : t("Back")}
        </Button>
      </div>

      <Card className="bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-xl sm:text-2xl">
            <User className="w-5 h-5 text-[#ffd100]" />
            {t("Passenger Details")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label htmlFor="passenger-full-name">
              <p className="text-white">{t("Full Name")}</p>
            </label>
            <input
              id="passenger-full-name"
              value={passengerDetails.fullName}
              maxLength={255}
              autoComplete="name"
              onChange={(event) => updateField("fullName", event.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="passenger-email">
              <p className="text-white">{t("Email")}</p>
            </label>
            <input
              id="passenger-email"
              type="email"
              value={passengerDetails.email}
              maxLength={254}
              autoComplete="email"
              onChange={(event) => updateField("email", event.target.value)}
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-[220px_1fr] gap-4">
            <div>
              <label htmlFor="passenger-country-code">
                <p className="text-white">{t("Country Code")}</p>
              </label>
              <select
                id="passenger-country-code"
                value={passengerDetails.countryCode}
                onChange={(event) => updateField("countryCode", event.target.value)}
                className={inputClass}
              >
                <option value="+44 United Kingdom">{t("+44 United Kingdom")}</option>
                <option value="+1 United States">{t("+1 United States")}</option>
                <option value="+971 United Arab Emirates">{t("+971 United Arab Emirates")}</option>
                <option value="+966 Saudi Arabia">{t("+966 Saudi Arabia")}</option>
                <option value="+974 Qatar">{t("+974 Qatar")}</option>
                <option value="+965 Kuwait">{t("+965 Kuwait")}</option>
                <option value="+973 Bahrain">{t("+973 Bahrain")}</option>
                <option value="+968 Oman">{t("+968 Oman")}</option>
                {getCountries()
                  .filter(code => !["GB", "US", "AE", "SA", "QA", "KW", "BH", "OM"].includes(code))
                  .sort((a, b) => countryLabels[a].localeCompare(countryLabels[b], locale))
                  .map(code => <option key={code} value={`+${getCountryCallingCode(code)} ${enCountries[code]}`}>
                    +{getCountryCallingCode(code)} {countryLabels[code]}
                  </option>)}
              </select>
            </div>
            <div>
            <label htmlFor="passenger-mobile">
              <p className="text-white">{t("Mobile Number")}</p>
            </label>
            <input
              id="passenger-mobile"
              type="tel"
              value={passengerDetails.mobileNumber}
              maxLength={32}
              autoComplete="tel"
              inputMode="tel"
              onChange={(event) => updateField("mobileNumber", event.target.value)}
              className={inputClass}
            />
            </div>
          </div>

          {validationError && (
            <p role="alert" className="text-red-300 text-sm font-semibold">
              {validationError}
            </p>
          )}

          <Button
            type="button"
            onClick={onSubmit}
            className="w-full bg-[#ffd100] hover:bg-[#ffd100]/90 text-[#2D2E2E] font-bold py-6 text-base sm:text-lg shadow-xl cursor-pointer"
          >
            {t("Continue")}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

