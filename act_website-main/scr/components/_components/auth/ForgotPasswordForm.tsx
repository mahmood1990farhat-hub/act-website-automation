"use client";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { postData } from "@/lib/api/postData";
import InputField from "./InputField";
import { IoMail } from "react-icons/io5";
import { toast } from "react-toastify";

type FormData = {
  email: string;
};

export default function ForgotPasswordForm({ 
  trans, 
  setTap,
  locale 
}: { 
  trans: any;
  setTap: (tep: number) => void;
  locale?: string;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState<string>("");

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>();

  const onSubmit = async (data: FormData) => {
    setIsLoading(true);
    try {
      await postData({
        endpoint: "/api/auth/forget-password/",
        body: {
          email: data.email,
        },
        queryParams: locale ? { locale } : undefined,
      });
      setEmailSent(data.email);
      // Navigate to reset password step (step 5 = reset password) with email in query
      setTimeout(() => {
        // Store email in sessionStorage to pass to reset form
        if (typeof window !== "undefined") {
          sessionStorage.setItem("resetPasswordEmail", data.email);
        }
        setTap(5); // Reset password step
      }, 1000);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full space-y-5">
      <div className="">
        <h1 className="text-3xl lg:text-5xl mb-3 font-extrabold text-center py-1">
          {trans.title}
        </h1>
        <p className="text-sm text-center text-muted px-10">
          {trans.description}
        </p>
      </div>
      
      {emailSent ? (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
          <p className="text-sm text-green-400 text-center">
            OTP code has been sent to {emailSent}. Please check your email.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <InputField
            label={trans.emailLabel || "Email"}
            placeholder={trans.emailPlaceholder || "your-email@example.com"}
            register={register}
            name="email"
            requiredMsg={trans.emailRequired || "Email is required"}
            error={errors.email}
            type="email"
            icon={<IoMail className="mx-2 text-lg" />}
          />

          <Button
            type="submit"
            disabled={isLoading}
            className="text-2xl w-full p-6"
          >
            {isLoading ? "Sending..." : trans.sendOtpButton}
          </Button>
        </form>
      )}
    </div>
  );
}
