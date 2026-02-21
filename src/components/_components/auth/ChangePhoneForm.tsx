"use client";
import { Button } from "@/components/ui/button";
import React, { useState, useRef, useEffect } from "react";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
import { getCookie, setCookie } from "cookies-next";
import { toast } from "react-toastify";
import PhoneInputWithCountrySelect from "react-phone-number-input";
import "react-phone-number-input/style.css";
import { BsFillTelephoneFill } from "react-icons/bs";
import { isValidPhoneNumber } from "react-phone-number-input";

type FormData = {
  phone_number: string;
};

type ChangePhoneFormProps = {
  locale: Locale;
  trans: any;
  onSuccess?: () => void;
  currentPhone?: string;
};

export default function ChangePhoneForm({
  locale,
  trans,
  onSuccess,
  currentPhone,
}: ChangePhoneFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);
  const [step, setStep] = useState<"request" | "verify">("request");
  const [timeLeft, setTimeLeft] = useState(120);
  const [requestedPhone, setRequestedPhone] = useState<string>("");
  const [phone, setPhone] = useState<string>(currentPhone || "");
  const [phoneError, setPhoneError] = useState<string>("");
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  const token = getCookie("userToken") as string | undefined;

  const handleOtpChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    idx: number
  ) => {
    const value = e.target.value;
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[idx] = value;
    setOtp(newOtp);

    if (value && idx < otp.length - 1) {
      otpRefs.current[idx + 1]?.focus();
    }
  };

  const handleBackspace = (
    e: React.KeyboardEvent<HTMLInputElement>,
    idx: number
  ) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      otpRefs.current[idx - 1]?.focus();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  useEffect(() => {
    if (timeLeft <= 0 || step !== "verify") return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft, step]);

  const onRequestChange = async () => {
    if (!token) {
      toast.error("Please login to change your phone number");
      return;
    }

    // Validate phone number
    if (!phone || !isValidPhoneNumber(phone)) {
      setPhoneError(trans.phoneInvalid || "Invalid phone number format");
      return;
    }
    setPhoneError("");

    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/request-change/",
        body: {
          phone_number: phone,
        },
        token,
        queryParams: { locale },
      });
      setRequestedPhone(phone);
      setStep("verify");
      setTimeLeft(120);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const onConfirmChange = async () => {
    if (!token) {
      toast.error("Please login to confirm phone change");
      return;
    }

    const code = otp.join("");
    if (code.length !== 6) {
      toast.error(trans.codeRequired || "Please enter the 6-digit code");
      return;
    }

    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/confirm-change/",
        body: {
          code,
          target: "phone",
        },
        token,
        queryParams: { locale },
      });
      // Update phone number in cookies
      const newPhone = requestedPhone;
      if (newPhone) {
        setCookie("user_phone_number", newPhone, { maxAge: 60 * 60 * 24 });
        setPhone(newPhone);
      }
      setOtp(Array(6).fill(""));
      setStep("request");
      setRequestedPhone("");
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (!requestedPhone) return;
    setOtp(Array(6).fill(""));
    setTimeLeft(120);
    try {
      await postData({
        endpoint: "/api/auth/request-change/",
        body: {
          phone_number: requestedPhone,
        },
        token,
        queryParams: { locale },
      });
    } catch (error) {
      console.error("Error resending code:", error);
    }
  };

  if (step === "verify") {
    return (
      <div className="w-full space-y-5">
        <div>
          <h2 className="text-lg font-bold text-center py-1">
            {trans.verifyTitle || "Verify Phone Change"}
          </h2>
          <p className="text-sm text-center text-muted px-10">
            {trans.verifyDesc || "Enter the code sent to your new phone number"}
          </p>
        </div>

        <div className="flex justify-between gap-2 mb-4" dir="ltr">
          {Array.from({ length: 6 }).map((_, idx) => (
            <input
              key={idx}
              type="text"
              maxLength={1}
              className="w-12 h-12 text-center text-xl border-2 border-border rounded-lg bg-foreground focus:ring-2 focus:ring-primary focus:border-primary"
              value={otp[idx] || ""}
              onChange={(e) => handleOtpChange(e, idx)}
              onKeyDown={(e) => handleBackspace(e, idx)}
              ref={(el) => {
                if (el) otpRefs.current[idx] = el;
              }}
            />
          ))}
        </div>

        <p className="text-sm text-center my-2">
          {timeLeft > 0 ? (
            <>
              {trans.otpNotReceived || "Didn't receive a code?"}
              <span
                className="underline text-primary cursor-pointer px-0.5"
                onClick={handleResend}
              >
                {trans.resend || "Resend it"}
              </span>
              <br />
              <span className="font-bold text-secondary text-lg">
                {formatTime(timeLeft)}
              </span>
            </>
          ) : (
            <button
              type="button"
              onClick={handleResend}
              className="text-primary underline cursor-pointer"
            >
              {trans.resend || "Resend"}
            </button>
          )}
        </p>

        <div className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setStep("request");
              setOtp(Array(6).fill(""));
            }}
            className="flex-1"
          >
            {trans.cancel || "Cancel"}
          </Button>
          <Button
            type="button"
            onClick={onConfirmChange}
            disabled={isLoading || otp.join("").length !== 6}
            className="flex-1 text-2xl p-6"
          >
            {isLoading ? trans.verifying || "Verifying..." : trans.confirmBtn || "Confirm"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-5">
      <div>
        <h2 className="text-lg font-bold text-center py-1">
          {trans.title || "Change Phone Number"}
        </h2>
        <p className="text-sm text-center text-muted px-10">
          {trans.desc || "Enter your new phone number below"}
        </p>
      </div>
      {currentPhone && (
        <div className="text-sm text-center text-muted">
          Current phone: {currentPhone}
        </div>
      )}
      <div className="space-y-5">
        <div>
          <label className="block mb-1 text-[16px] text-gray-300">
            {trans.phoneLabel || "New Phone Number"} <span className="text-primary">*</span>
          </label>
          <div
            className="flex items-center w-full p-3 border-2 bg-foreground text-white border-muted rounded-lg hover:border-primary/50 transition-colors"
            dir="ltr"
          >
            <PhoneInputWithCountrySelect
              defaultCountry="GB"
              value={phone}
              onChange={(val) => {
                setPhone(val || "");
                setPhoneError("");
              }}
              international
              countryCallingCodeEditable={false}
              className="w-full [&_.PhoneInputInput]:bg-transparent [&_.PhoneInputInput]:text-white [&_.PhoneInputInput]:border-none [&_.PhoneInputInput]:outline-none [&_.PhoneInputInput]:focus:outline-none [&_.PhoneInputInput]:focus:ring-0 [&_.PhoneInputInput]:placeholder:text-gray-400 [&_.PhoneInputCountrySelect]:bg-transparent [&_.PhoneInputCountrySelect]:text-white [&_.PhoneInputCountrySelect]:border-none [&_.PhoneInputCountrySelect]:outline-none [&_.PhoneInputCountrySelect]:focus:outline-none [&_.PhoneInputCountryIcon]:opacity-80"
            />
            <BsFillTelephoneFill className="mx-2 text-gray-300" />
          </div>
          {phoneError && (
            <p className="text-error text-sm mt-1">{phoneError}</p>
          )}
        </div>
        <Button
          type="button"
          onClick={onRequestChange}
          disabled={isLoading || !phone}
          className="text-2xl w-full p-6"
        >
          {isLoading ? trans.sending || "Sending..." : trans.sendCode || "Send Verification Code"}
        </Button>
      </div>
    </div>
  );
}

