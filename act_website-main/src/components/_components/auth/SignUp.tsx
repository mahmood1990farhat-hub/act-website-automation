"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { BsEyeFill, BsEyeSlashFill, BsFillTelephoneFill } from "react-icons/bs";
import PhoneInput, { isValidPhoneNumber } from "react-phone-number-input";

import "react-phone-number-input/style.css";
import PhoneInputWithCountrySelect from "react-phone-number-input";
import { postData } from "@/lib/api/postData";
import { Button } from "@/components/ui/button";
import InputField from "./InputField";
import PasswordField from "./PasswordField";
import { Locale } from "../../../../i18n.config";
import { IoLocation, IoMail } from "react-icons/io5";

type FormData = {
  first_name: string;
  last_name: string;
  email: string;
  location: string;
  phone: string;
  password: string;
  confirmPassword: string;
};

export default function SignUpT({
  setTap,
  locale,
  trans,
  isCaptain,
  setSevePhoneforOTP
}: {
  setTap: (tep: number) => void;
  locale: Locale;
  trans: any;
  setSevePhoneforOTP:(ph:string)=>void
  isCaptain?: string;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const [phone, setPhone] = useState<string>("");
  const [phoneError, setPhoneError] = useState<string>("");

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>();

  const password = watch("password");

  useEffect(() => {
    setValue("phone", phone);
  }, [phone, setValue]);

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    if (!isValidPhoneNumber(phone)) {
      setPhoneError(trans.phoneInvalid || "Phone Number is Invalid")
    } else {
      setPhoneError('');
      setLoading(true);
      try {
        // Note: Driver signup now uses the 2-step process via DriverOnboardingStep1
        // This component is now only for passenger registration
        const endpointURL = "/api/passengers/register-passenger/";

        const body = {
          user_data: {
            phone_number: phone,
            first_name: data.first_name,
            last_name: data.last_name,
            email: data.email,
            password: data.password,
            confirm_password: data.confirmPassword,
            address: data.location,
          },
        };

        const res = await postData<any>({
          endpoint: endpointURL,
          body: body,
          queryParams: {
            locale: locale,
          },
        });
        
        // Set passenger account type if not already set
        if (res && !res.account_type) {
          // This will be handled by the backend, but we can ensure it's set correctly
        }
        
        setSevePhoneforOTP(phone)
        setTap(1);
      } catch (err) {
        console.error(err);
      }
      finally{
        setLoading(false);
      }
    }
  };

  return (
    <>
      {" "}
      <h1 className="text-3xl lg:text-5xl mb-3 font-extrabold text-center py-1">
        {trans.createAccount}
      </h1>
      <p className="text-muted text-center mt-1  mb-10">{trans.desc_main}</p>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-2 text-sm">
        <div className="flex items-center w-full gap-5  ">
          <div className="w-full">
            <InputField
              label={trans.firstName}
              placeholder={""}
              register={register}
              name="first_name"
              error={errors.first_name}
              requiredMsg={trans.fullNameRequired}
            />
          </div>
          <div className="w-full">
            <InputField
              label={trans.lastName}
              placeholder={""}
              register={register}
              name="last_name"
              error={errors.last_name}
              requiredMsg={trans.fullNameRequired}
            />
          </div>
        </div>
        <InputField
          label={trans.email}
          placeholder={trans.email}
          register={register}
          name="email"
          requiredMsg={trans.fullNameRequired}
          error={errors.email}
          icon={<IoMail className="mx-2 text-lg" />}
        />
        <div>
          <label className="text-sm font-medium mb-1">
            {trans.enterPhone} <span className="text-primary">*</span>
          </label>
          <div
            className="flex items-center w-full p-3 border-2 bg-foreground border-muted rounded-lg mt-1"
            dir="ltr"
          >
            <PhoneInputWithCountrySelect
              defaultCountry="GB"
              value={phone}
              onChange={(val) => setPhone(val || "")}
              international
              countryCallingCodeEditable={false}
              className="w-full bg-foreground focus:outline-none"
              />
            <BsFillTelephoneFill className="mx-2" />
          </div>
          {phoneError && <p className="text-xs text-error mt-1.5">{phoneError}</p>}
        </div>
        <InputField
          label={trans.location}
          placeholder={trans.location}
          register={register}
          name="location"
          requiredMsg={trans.locationRequired}
          error={errors.location}
          icon={<IoLocation className="text-lg  " />}
        />

        <PasswordField
          label={trans.password}
          name="password"
          register={register}
          show={showPassword}
          setShow={setShowPassword}
          validate={{
            required: trans.passwordRequired,
            minLength: { value: 6, message: trans.passwordMinLength },
          }}
          error={errors.password}
        />

        <PasswordField
          label={trans.confirmPassword}
          name="confirmPassword"
          register={register}
          show={showConfirmPassword}
          setShow={setShowConfirmPassword}
          validate={{
            validate: (value: string) =>
              value === password || trans.passwordMismatch,
          }}
          error={errors.confirmPassword}
        />

        <Button type="submit" className="text-2xl w-full mt-5 p-6 cursor-pointer" disabled={loading}>
          {trans.createAccountBtn}
        </Button>
        <p className="text-center text-sm mt-4 text-muted">
          {trans.alreadyHaveAccount}{" "}
          <span
            onClick={() => setTap(1)}
            className=" text-primary  px-1 underline cursor-pointer"
          >
            {trans.login}
          </span>
        </p>
      </form>
    </>
  );
}
