import { Button } from "@/components/ui/button";
import Image from "next/image";
import React from "react";
import ContactUs from "./ContactUs";
type typeProps = {
  about_us: {
    about_us_title: string;

    company_description_1: {
      title: string;
      titlespan: string;
      desc: string;
    };

    company_description_2: {
      desc1: string;
      desc2: string;
      desc3: string;
    };

    company_description_3: string;
    company_description_4: string;

    get_in_touch: {
      title: string;
      titlespan: string;
      form: {
        FullName: string;
        mail: string;
        Yourmessage: string;
        button: string;
      };
    };

    booking_title: {
      title: string;
      titlespan: string;
    };

    sections: {
      title: string;
      text: string;
    }[];
  };
};
export default function About({ about_us }: typeProps) {
  return (
    <section  className="relative p-8 lg:px-14 px-5 space-y-5">
      <h1 id="about-us" className="lg:text-2xl text-lg font-bold">
        {about_us.about_us_title}
      </h1>
      <div className="flex items-start max-md:flex-col gap-4  h-full">
        <div className={`md:w-1/2 md:border-e  md:pe-4 border-black`}>
          <div className="flex items-start  gap-5 ">
            <div className="hidden lg:block relative w-[500px] h-[100px]   me-auto ">
              <Image
                src="/images/logo.png"
                alt="landing_image"
                fill
                className="object-contain "
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
                quality={100}
                priority
              />
            </div>
            <div>
              <h1 className="font-bold text-4xl mb-4">
                {about_us.company_description_1.title}{" "}
                <span className="text-primary">
                  {" "}
                  {about_us.company_description_1.titlespan}{" "}
                </span>
              </h1>
              <p>{about_us.company_description_1.desc}</p>
            </div>
          </div>
          <br />
          <p  className="">
            {about_us.company_description_2.desc1}
            <span className="font-bold">
              {about_us.company_description_2.desc2}
            </span>
            {about_us.company_description_2.desc3}
          </p>
          <br />
          <p>{about_us.company_description_3}</p>
          <p>{about_us.company_description_4}</p>
          <div className="mt-5" id='contact-us'>
            <h1 className="font-bold text-4xl mb-4">
              {about_us.get_in_touch.title}
              <span className="text-primary">
                {" "}
                {about_us.get_in_touch.titlespan}
              </span>
            </h1>
            <ContactUs form={about_us.get_in_touch.form} />
          </div>
        </div>

        <div className=" md:w-1/2 ">
          <h1 className="font-bold text-4xl mb-4">
            {about_us.booking_title.title}
            <span className="text-primary">
              {" "}
              {about_us.booking_title.titlespan}
            </span>
          </h1>
          <div className="space-y-2">
            {about_us.sections.map((item, index) => (
              <div key={index}>
                <h2 className="font-bold text-lg ">{item.title}</h2>
                <p className="text-lg">{item.text}</p>
              </div>
            ))}
          </div>
          <div className="relative w-full h-[250px]  ">
            <Image
              src="/images/logo-about.png"
              alt="landing_image"
              fill
              className="object-contain "
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
              quality={100}
              priority
            />
          </div>
        </div>
      </div>
    </section>
  );
}
