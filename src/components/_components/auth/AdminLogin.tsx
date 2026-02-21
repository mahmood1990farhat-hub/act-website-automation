"use client";
import { useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { postData } from "@/lib/api/postData";
import { setCookie } from "cookies-next";
import { Button } from "@/components/ui/button";
import PasswordField from "./PasswordField";
import InputField from "./InputField";

import { IoMail } from "react-icons/io5";
import { useRouter } from "next/navigation";
import GlobalModal from "../GlobalModal";
import { toast } from "react-toastify";
import CarLoading from "../loading/CarLoading";

type AdminLoginData = {
  username: string;
  password: string;
};

export default function AdminLogin({
  locale,
  trans,
  setStep,
}: {
  locale: string;
  trans: any;
  setStep?: () => void;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setIsLoading] = useState(false);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AdminLoginData>();

  const onSubmit: SubmitHandler<AdminLoginData> = async (data) => {
    setIsLoading(true);
    try {
      // Use the same API endpoint as passenger login but for admin
      const endpoint = "/api/auth/login/";

      const body = {
        username: data.username,
        password: data.password,
        account_type: "normal",
      };

      const res = await postData<any>({
        endpoint: endpoint,
        body: body,
        queryParams: {
          locale,
        },
      });

      setCookie("userToken", res.access_token, { maxAge: 60 * 60 * 24 });

      // Handle admin accounts - check if account_type is admin
      if (res.account_type === "normal") {
        setCookie("user_id", res.user_id, { maxAge: 60 * 60 * 24 });
        setCookie("account_type", res.account_type, { maxAge: 60 * 60 * 24 });

        // Redirect to admin dashboard; keep loading overlay until navigation unmounts this component
        if (setStep) {
          setStep();
        }
        router.push(`/${locale}/dashboard/overview`);
        router.refresh();
        return;
      }

      // If not admin account, show error
      toast.error("Access denied: Admin account required");
      setIsLoading(false);
    } catch (error) {
      console.error("Admin Login Error:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="relative w-full">
      <h1 className="text-3xl lg:text-5xl mb-3 font-extrabold text-center py-1">
        {trans.title || "Admin Login"}
      </h1>
      <p className="text-muted text-center mt-1 mb-6 w-full">
        {trans.desc_main || "Please enter your admin credentials to login"}
      </p>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4 text-sm w-full"
      >
        <InputField
          label={trans.usernameMail || "Email"}
          placeholder={trans.usernamePlaceholder || "admin@example.com"}
          register={register}
          name="username"
          requiredMsg={trans.usernameRequired || "Email is required"}
          error={errors.username}
          type="email"
          icon={<IoMail className="mx-2 text-lg" />}
        />

        <div>
          <PasswordField
            label={trans.passwordLabel || "Password"}
            name="password"
            register={register}
            show={showPassword}
            setShow={setShowPassword}
            validate={{
              required: trans.passwordRequired || "Password is required",
              minLength: { value: 4, message: trans.passwordRequired || "Password is required" },
            }}
            error={errors.password}
          />
        </div>

        <Button type="submit" className="text-2xl w-full p-6 cursor-pointer" disabled={loading}>
          {trans.loginButton || "Login"}
        </Button>
      </form>
      {loading && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 backdrop-blur-sm rounded-lg"
          aria-busy="true"
          aria-live="assertive"
        >
          <div className="flex flex-col items-center gap-4 px-6 py-8 bg-foreground/95 backdrop-blur-md rounded-2xl border border-primary/20 shadow-2xl">
            <CarLoading />
            <p className="text-sm text-white/80">
              Securing your admin session...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
