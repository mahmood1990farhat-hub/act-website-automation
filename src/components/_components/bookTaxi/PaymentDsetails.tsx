import React from "react";
import { Payments_details } from ".";
import { Button } from "@/components/ui/button";
import { FaArrowLeft } from "react-icons/fa";
import Image from "next/image";
import { useForm } from "react-hook-form";
import StripeWrapper from "../stripe/StripeWrapper";
import CheckoutForm from "../stripe/CheckoutForm";
import { languageType, Locale } from "../../../../i18n.config";
import { Languages } from "@/constants/enums";

type typeProps = {
  trans: Payments_details;
    nextStep: () => void;
  prevStep: () => void;
  clientSecret:string
  policy_and_terms:any
  locale?: Locale;
};

type FormData = {
  cardNumber: string;
  expiryDate: string;
  cvc: string;
  agree: boolean;

};

export default function PaymentDsetails({ trans, nextStep,prevStep, clientSecret ,policy_and_terms, locale = Languages.ENGLISH}: typeProps) {
  // const {
  //   register,
  //   handleSubmit,
  //   formState: { errors },
  // } = useForm<FormData>();

  // const onSubmit = (data: FormData) => {
  //   console.log("Form Data:", data);
  //   // هنا يمكنك تنفيذ أي إجراء بعد التأكد من صحة الفورم
  // };

  return (
       <div className="max-w-lg mx-auto mt-10">
         <StripeWrapper clientSecret={clientSecret}>
           <CheckoutForm nextStep={nextStep} prevStep={prevStep } trans={trans} clientSecret={clientSecret} policy_and_terms={policy_and_terms} locale={locale}/>
         </StripeWrapper>
       </div>
  );
}
