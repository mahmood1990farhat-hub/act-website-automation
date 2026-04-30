"use client";
import Image from "next/image";
import React, { useEffect, useState } from "react";
import PasswordField from "../PasswordField";
import InputField from "../InputField";
import { IoLocation, IoMail } from "react-icons/io5";
import { BsFillTelephoneFill } from "react-icons/bs";
import PhoneInputWithCountrySelect from "react-phone-number-input";
import { useForm } from "react-hook-form";
import FileField from "../FileField";
import { Button } from "@/components/ui/button";
import { extract_error } from "@/lib/api/errorApi";
import GlobalModal from "../../GlobalModal";
import { FaTimesCircle } from "react-icons/fa";
import { DateInput } from "../../dateAndTime/date-input";
import { TimeInput } from "../../dateAndTime/time-input";
import YearPicker from "../../dateAndTime/year-picker";
import { Locale } from "../../../../../i18n.config";
import GetStartedCaptain from "./GetStartedCaptain";
import { getCookie } from "cookies-next";
import Link from "next/link";

type FormData = {
  first_name: string;
  last_name: string;
  email: string;
  address: string;
  phone: string;
  password: string;
  confirm_password: string;
  bank_account_number: string;
  sort_code: string;
  registered_address: string;
  vehicle_number: string;
  year_of_manufacture: string;
  pco: FileList;
  dbs: FileList;
  dvla: FileList;
  MOT: FileList;
  PHV: FileList;
};
interface TimeValue {
  hour: number;
  minute: number;
  period: "AM" | "PM";
}
export default function CreateCaptainAccount({
  trans,
  transInfo,
  setTapAction,
  locale,
}: {
  locale: Locale;
  trans: any;
  transGetStarted: any;
  transInfo: any;
  setTapAction: (tep: number) => void;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [errorSignMess, setErrorSignMess] = useState<string | undefined>();
  const [dateTimeError, setDateTimeError] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>();
  const [selectedTime, setSelectedTime] = useState<any>();
  const [valueDateTime, setValueDateTime] = useState<{
    date: string;
    time: string;
  }>({
    date: "",
    time: "",
  });

  const [openModal,setOpenModal]=useState(false)
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 4;
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>();

  const [token, setToken] = useState<string | undefined>();

  useEffect(() => {
    setToken(getCookie("userToken") as string | undefined);
  }, []);

  const password = watch("password");

  // Step navigation functions
  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const goToStep = (step: number) => {
    setCurrentStep(step);
  };

  const onSubmit = async (data: FormData) => {
    if (!selectedDate || !selectedTime) {
      setDateTimeError(true);
      return;
    }

    setIsLoading(true);
    const formData = new FormData();

    // formData.append("first_name", data.first_name);
    // formData.append("last_name", data.last_name);
    // formData.append("email", data.email);
    // formData.append("address", data.address);
    // formData.append("phone_number", phone);
    // formData.append("password", data.password);
    // formData.append("confirm_password", data.confirm_password);
    formData.append("bank_account_number", data.bank_account_number);
    formData.append("sort_code", data.sort_code);
    formData.append("registered_address", data.registered_address);
    formData.append("vehicle_number", data.vehicle_number);
    formData.append("year_of_manufacture", data.year_of_manufacture);
    formData.append("interview_date", valueDateTime.date);
    formData.append("interview_time", valueDateTime.time);

    if (data.pco && data.pco.length > 0) {
      formData.append("pco", data.pco[0]);
    }
    if (data.dbs && data.dbs.length > 0) {
      formData.append("dbs", data.dbs[0]);
    }
    if (data.dvla && data.dvla.length > 0) {
      formData.append("dvla", data.dvla[0]);
    }
    if (data.MOT && data.MOT.length > 0) {
      formData.append("mot", data.MOT[0]);
    }
    if (data.PHV && data.PHV.length > 0) {
      formData.append("phv", data.PHV[0]);
    }

    const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

    fetch(`${BASE_URL}/api/drivers/onboarding/step2/`, {
      method: "POST",
      body: formData,
    headers: {
    Authorization: token ? `Bearer ${token}` : "",
  },
    })
      .then(async (res) => {
        const result = await res.json();
        if (!res.ok) {
          setErrorSignMess(extract_error(result));

          throw result;
        }
        return result;
      })
      .then((data) => {
        setIsLoading(false);
        setOpenModal(true)
     
      })
      .catch((error) => {
        setIsLoading(false);
        console.error("Error:", error);
      });
  };


  return (
   <>
   <GlobalModal isOpen={openModal} onClose={()=>setOpenModal(false)}> 

    <div className="flex items-center justify-center flex-col gap-4 ">
      <h1 className="text-lg font-bold" >{trans.modal.title}</h1>
      <p className="text-center">{trans.modal.desc}</p>
      <Link href={`/${locale}`} className="bg-primary text-black font-bold   p-2 rounded">{trans.modal.btu}</Link>
    </div>
   </GlobalModal>
    <div className="w-full min-h-screen max-h-screen overflow-y-auto">
      <div className="">
        {" "}
        {/* <GetStartedCaptain trans={transGetStarted} /> */}
      </div>
      <GlobalModal
        isOpen={errorSignMess ? true : false}
        onClose={() => setErrorSignMess(undefined)}
      >
        <div className="flex items-center justify-center flex-col gap-5">
          <FaTimesCircle className="text-5xl text-red-700" />
          <h1>{errorSignMess}</h1>
          <Button
            onClick={() => setErrorSignMess(undefined)}
            className="p-5 px-10 text-lg"
          >
            Close
          </Button>
        </div>
      </GlobalModal>

      {/* Step Progress Indicator */}
      <div className="mb-4 sm:mb-8 px-2 sm:px-0">
        <div className="flex items-center justify-center space-x-2 sm:space-x-4 mb-4">
          {Array.from({ length: totalSteps }, (_, index) => (
            <div key={index} className="flex items-center">
              <button
                onClick={() => goToStep(index + 1)}
                className={`w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-medium transition-colors ${
                  currentStep >= index + 1
                    ? "bg-primary text-black"
                    : "bg-gray-300 text-gray-600"
                }`}
              >
                {index + 1}
              </button>
              {index < totalSteps - 1 && (
                <div
                  className={`w-6 sm:w-12 h-1 mx-1 sm:mx-2 ${
                    currentStep > index + 1 ? "bg-primary" : "bg-gray-300"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="text-center">
          <h1 className="text-lg sm:text-xl font-semibold mb-2">
            {trans.title}
          </h1>
          <p className="text-xs sm:text-sm ">
            Step {currentStep} of {totalSteps}
          </p>
        </div>
      </div>

      <form
        className="space-y-4 sm:space-y-6 lg:px-25 px-2 pb-8 sm:pb-12"
        onSubmit={handleSubmit(onSubmit)}
      >
        {/* Step 1: Driver Documents */}
        {currentStep === 1 && (
          <div className="border border-muted md:p-5 p-3 rounded-lg mb-4">
            <h1 className="text-lg text-primary font-medium text-center mb-6">
              {trans.DriverDocuments?.title || "Driver Documents"}
            </h1>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <div className="pt-3">
                  <label className="text-sm font-medium    block mb-1">
                    {trans.DriverDocuments?.pcoLabel || "PCO driver licence issued by TfL (mandatory)"}
                  </label>
                  <p className="text-xs  ">
                    {trans.DriverDocuments?.pcoDescription ||
                      "Upload the front of your TfL private hire driver licence showing name, badge number, expiry date, and photo."}
                  </p>
                </div>
                <div>
                  <FileField
                    label=""
                    placeholder="pco"
                    name="pco"
                    register={register}
                    requiredMsg={transInfo.locationRequired}
                    error={errors.pco}
                    value={watch("pco")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <div className="pt-3">
                  <label className="text-sm font-medium    block mb-1">
                    {trans.DriverDocuments?.dbsLabel || "DBS enhanced certificate (background check)"}
                  </label>
                  <p className="text-xs  ">
                    {trans.DriverDocuments?.dbsDescription ||
                      "Upload a recent Disclosure and Barring Service certificate (issued within the last 6 months)."}
                  </p>
                </div>
                <div>
                  <FileField
                    label=""
                    placeholder="dbs"
                    name="dbs"
                    register={register}
                    requiredMsg={transInfo.locationRequired}
                    error={errors.dbs}
                    value={watch("dbs")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <div className="pt-3">
                  <label className="text-sm font-medium    block mb-1">
                    {trans.DriverDocuments?.dvlaLabel || "UK DVLA driving licence (both sides)"}
                  </label>
                  <p className="text-xs  ">
                    {trans.DriverDocuments?.dvlaDescription ||
                      "Upload clear photos of the front and back of your UK driving licence showing all details."}
                  </p>
                </div>
                <div>
                  <FileField
                    label=""
                    placeholder="dvla"
                    name="dvla"
                    register={register}
                    requiredMsg={transInfo.locationRequired}
                    value={watch("dvla")}
                    error={errors.dvla}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Vehicle Documents */}
        {currentStep === 2 && (
          <div className="border border-muted md:p-5 p-3 rounded-lg mb-4">
            <h1 className="text-lg text-primary font-medium text-center mb-6">
              {trans.VehicleDocuments.title}
            </h1>
            
            {/* Vehicle Information Section */}
            <div className="mb-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <label className="text-sm font-medium    pt-3">
                  {trans.VehicleDocuments.VehicleNumber}
                </label>
                <div>
                  <InputField
                    label=""
                    placeholder={"Enter vehicle registration number"}
                    register={register}
                    name="vehicle_number"
                    value={watch("vehicle_number")}
                    requiredMsg={transInfo.locationRequired}
                    error={errors.vehicle_number}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <label className="text-sm font-medium    pt-3">
                  {trans.VehicleDocuments.Register}
                </label>
                <div>
                  <YearPicker
                    value={watch("year_of_manufacture")}
                    onChange={(year) => {
                      setValue("year_of_manufacture", year, { shouldValidate: true });
                    }}
                    placeholder={trans.VehicleDocuments.RegisterDescription || "Select year"}
                    min={1950}
                    max={new Date().getFullYear()}
                    language={locale}
                    error={errors.year_of_manufacture}
                    requiredMsg={transInfo.locationRequired}
                  />
                </div>
              </div>
            </div>

            {/* Vehicle Documents Section */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <div className="pt-3">
                  <label className="text-sm font-medium    block mb-1">
                    {trans.VehicleDocuments?.motLabel || "MOT Certificate"}
                  </label>
                  <p className="text-xs  ">
                    {trans.VehicleDocuments?.motDescription ||
                      "Upload the latest MOT certificate confirming the vehicle has passed its safety inspection."}
                  </p>
                </div>
                <div>
                  <FileField
                    label=""
                    placeholder="mot"
                    name="MOT"
                    register={register}
                    requiredMsg={transInfo.locationRequired}
                    error={errors.MOT}
                    value={watch("MOT")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <div className="pt-3">
                  <label className="text-sm font-medium    block mb-1">
                    {trans.VehicleDocuments?.phvLabel || "PHV Licence"}
                  </label>
                  <p className="text-xs  ">
                    {trans.VehicleDocuments?.phvDescription ||
                      "Upload the TfL PHV licence for your vehicle. If you rent, request this document from your operator."}
                  </p>
                </div>
                <div>
                  <FileField
                    label=""
                    placeholder="phv"
                    name="PHV"
                    register={register}
                    requiredMsg={transInfo.locationRequired}
                    error={errors.PHV}
                    value={watch("PHV")}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Bank Details */}
        {currentStep === 3 && (
          <div className="border border-muted md:p-5 p-3 rounded-lg mb-4">
            <h1 className="text-lg text-primary font-medium text-center mb-6">
              {trans.BankDetails.title}
            </h1>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <label className="text-sm font-medium    pt-3">
                  {trans.BankDetails.AccountBankNumber}
                </label>
                <div>
                  <InputField
                    label=""
                    placeholder={"Enter your 8-digit bank account number"}
                    register={register}
                    name="bank_account_number"
                    requiredMsg={transInfo.locationRequired}
                    value={watch("bank_account_number")}
                    error={errors.bank_account_number}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <label className="text-sm font-medium    pt-3">
                  {trans.BankDetails.sortCode}
                </label>
                <div>
                  <InputField
                    label=""
                    placeholder={"XX-XX-XX (6 digits)"}
                    register={register}
                    name="sort_code"
                    requiredMsg={transInfo.locationRequired}
                    error={errors.sort_code}
                    value={watch("sort_code")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start">
                <label className="text-sm font-medium    pt-3">
                  {trans.BankDetails.RegistereDaddress}
                </label>
                <div>
                  <InputField
                    label=""
                    placeholder={"Enter your registered address"}
                    register={register}
                    name="registered_address"
                    requiredMsg={transInfo.locationRequired}
                    error={errors.registered_address}
                    value={watch("registered_address")}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Review Documents Date */}
        {currentStep === 4 && (
          <div className="border border-muted md:p-5 p-3 rounded-lg space-y-3 mb-4">
            <h1 className="text-lg text-primary font-medium text-center mb-6">
              {trans.reviewDocuments}
            </h1>
            <div className="grid lg:grid-cols-2 md:grid-cols-2 grid-cols-1 gap-5">
              <div>
                <DateInput
                  setFormattedDate={(d) =>
                    setValueDateTime({ ...valueDateTime, date: d })
                  }
                  value={selectedDate}
                  onChange={setSelectedDate}
                  language={locale}
                />
                {dateTimeError && !selectedDate && (
                  <p className="text-red-500">{transInfo.locationRequired}</p>
                )}
              </div>
              <div>
                <TimeInput
                  setFormattedTime={(d) =>
                    setValueDateTime({ ...valueDateTime, time: d })
                  }
                  value={selectedTime}
                  onChange={(time) => setSelectedTime(time)}
                  language={locale}
                />
                {dateTimeError && !selectedTime && (
                  <p className="text-red-500">{transInfo.locationRequired}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Step Navigation Buttons */}
        <div className="flex items-center justify-between mt-6 sm:mt-8 mb-4 sm:mb-0">
          <Button
            type="button"
            onClick={prevStep}
            disabled={currentStep === 1}
            className="px-6 py-3 bg-gray-500 text-white disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Previous
          </Button>
          
          {currentStep < totalSteps ? (
            <Button
              type="button"
              onClick={nextStep}
              className="px-6 py-3 bg-primary text-black"
            >
              Next
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={isLoading}
              className="px-6 py-3 bg-primary text-black disabled:bg-gray-300"
            >
              {isLoading ? (
                <div className="flex items-center">
                  <svg
                    className="animate-spin h-5 w-5 mr-2"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                    ></path>
                  </svg>
                  Loading...
                </div>
              ) : (
                transInfo.createAccountBtn
              )}
            </Button>
          )}
        </div>
      </form>
    </div></>
  );
}

{
  /* {step && (
            <div className="fixed inset-0 bg-black/10  bg-opacity-50 flex items-center justify-center z-50">
              <div
                onClick={(e) => e.stopPropagation()}
                className="bg-[#18181A] p-3 rounded-md w-1/2  flex items-center flex-col gap-5 m-10 relative shadow-lg text-right max-h-[100vh] overflow-y-auto on-scrollbar py-5"
              >
                <h1 className="text-center text-2xl font-bold ">
                  Choose date to review your documents
                </h1>
                <div className="flex md:items-center md:justify-center max-md:flex-col gap-5">
                  <div className=" ">
                    <DateInput
                      value={selectedDate}
                      onChange={setSelectedDate}
                      language={locale}
                      inCreateCaptain={true}
                    />
                  </div>
                  <div className="">
                    <TimeInput
                      value={selectedTime}
                      onChange={setSelectedTime}
                      language={locale}
                      inCreateCaptain={true}
                    />
                  </div>
                </div>
                <h2 className="text-center text-2xl font-bold space-x-2">
                  <span>
                    {selectedDate
                      ? selectedDate.toLocaleDateString(locale)
                      : ""}
                  </span>

                  <span>
                    {" "}
                    {selectedTime
                      ? selectedTime.hour +
                        ":" +
                        (selectedTime.minute < 10
                          ? "0" + selectedTime.minute
                          : selectedTime.minute) +
                        " " +
                        selectedTime.period
                      : ""}
                  </span>
                </h2>
                <div className="w-5/12 space-y-4">
                  <Button className="w-full text-lg p-6  ">Next</Button>
                  <Button onClick={()=>setStep(false)} type="button" className="w-full bg-muted-foreground hover:bg-gray-500 border text-primary border-primary p-6">Cancel</Button>
                </div>
              </div>
            </div>
          )} */
}
