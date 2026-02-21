"use client";
import { Button } from "@/components/ui/button";
import React, { useState, useRef, useEffect } from "react";
import { useForm } from "react-hook-form";
import { Locale } from "../../../../i18n.config";
import { postData } from "@/lib/api/postData";
import { getCookie, setCookie } from "cookies-next";
import { toast } from "react-toastify";

type FormData = {
  email: string;
};

type ChangeEmailFormProps = {
  locale: Locale;
  trans: any;
  onSuccess?: () => void;
  currentEmail?: string;
};

export default function ChangeEmailForm({
  locale,
  trans,
  onSuccess,
  currentEmail,
}: ChangeEmailFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);
  const [step, setStep] = useState<"request" | "verify">("request");
  const [timeLeft, setTimeLeft] = useState(120);
  const [requestedEmail, setRequestedEmail] = useState<string>("");
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>();

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

  const onRequestChange = async (data: FormData) => {
    if (!token) {
      toast.error("Please login to change your email");
      return;
    }

    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/request-change/",
        body: {
          email: data.email,
        },
        token,
        queryParams: { locale },
      });
      setRequestedEmail(data.email);
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
      toast.error("Please login to confirm email change");
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
          target: "email",
        },
        token,
        queryParams: { locale },
      });
      // Update email in cookies
      if (requestedEmail) {
        setCookie("user_email", requestedEmail, { maxAge: 60 * 60 * 24 });
      }
      setOtp(Array(6).fill(""));
      setStep("request");
      setRequestedEmail("");
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
    if (!requestedEmail) return;
    setOtp(Array(6).fill(""));
    setTimeLeft(120);
    try {
      await postData({
        endpoint: "/api/auth/request-change/",
        body: {
          email: requestedEmail,
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
            {trans.verifyTitle || "Verify Email Change"}
          </h2>
          <p className="text-sm text-center text-muted px-10">
            {trans.verifyDesc || "Enter the code sent to your new email address"}
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
          {trans.title || "Change Email"}
        </h2>
        <p className="text-sm text-center text-muted px-10">
          {trans.desc || "Enter your new email address below"}
        </p>
      </div>
      {currentEmail && (
        <div className="text-sm text-center text-muted">
          Current email: {currentEmail}
        </div>
      )}
      <form onSubmit={handleSubmit(onRequestChange)} className="space-y-5">
        <div>
          <label className="block mb-1 text-[16px]">
            {trans.emailLabel || "New Email"} <span className="text-primary">*</span>
          </label>
          <div className="flex items-center w-full min-h-[48px] p-2.5 border-2 bg-foreground border-muted rounded-lg hover:border-primary/50 transition-colors">
            <input
              type="email"
              {...register("email", {
                required: trans.emailRequired || "Email is required",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: trans.emailInvalid || "Invalid email address",
                },
              })}
              placeholder={trans.emailPlaceholder || "your-email@example.com"}
              className="w-full focus:outline-none bg-foreground"
            />
          </div>
          {errors.email && (
            <p className="text-error text-sm mt-1">{errors.email.message}</p>
          )}
        </div>
        <Button
          type="submit"
          disabled={isLoading}
          className="text-2xl w-full p-6"
        >
          {isLoading ? trans.sending || "Sending..." : trans.sendCode || "Send Verification Code"}
        </Button>
      </form>
    </div>
  );
}

