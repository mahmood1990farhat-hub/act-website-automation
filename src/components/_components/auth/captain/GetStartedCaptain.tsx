"use client";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import Link from "next/link";
import React, { useState } from "react";
import { FaCircleCheck } from "react-icons/fa6";

export default function GetStartedCaptain({ trans ,nextTep }: { trans: any,nextTep:()=>void }) {
  const [openInstruction, setOpenInstruction] = useState(false);

  return (
    <div className="w-full lg:px-20 px-4  space-y-4 flex items-center flex-col ">
      <div className="  w-full flex items-center ">
        <div className="relative max-md:hidden w-full   h-[190px] md:me-auto">
          <Image
            src="/images/logo-witn-text.png"
            alt="landing_image"
            fill
            className="object-contain"
            quality={100}
            priority
          />
        </div>
        <div className="relative  w-full  h-[190px] md:me-auto">
          <Image
            src="/images/captain/captain.png"
            alt="landing_image"
            fill
            className="object-contain"
            quality={100}
            priority
          />
        </div>
      </div>
      <div className="space-y-5 text-center ">
        <h1 className="md:text-4xl text-2xl font-bold md:text-start  w-full ">{trans.title}</h1>
        <p className="lg:px-15 px-2 ">{trans.desc}</p>
      </div>
      <div className="grid md:grid-cols-2 gap-10 items-center">
        <div className="relative  w-[300px] h-[150px] md:me-auto">
          <Image
            src="/images/captain/becomeMemeber.png"
            alt="landing_image"
            fill
            className="object-contain"
            quality={100}
            priority
          />
        </div>
        <Button onClick={nextTep} className="w-full text-lg p-5 px-10">{trans.button}</Button>
      </div>

      <div className="flex items-center justify-between max-md:flex-col-reverse  w-full my-10 ">
        <div className="md:w-1/2 space-y-5">
          <h1>{trans.HelpCenter}</h1>
          <ul className="text-muted space-y-3.5">
            <li>{trans.supportTeam}</li>
            <li>info@atgroup.com</li>
            <li>+(44) 746 494 0000</li>
          </ul>
        </div>
        <div className="relative   md:w-[400px] w-full   h-[150px] ">
          <Image
            src="/images/logo-witn-text.png"
            alt="landing_image"
            fill
            className="object-contain"
            quality={100}
            priority
          />
        </div>
      </div>
      <button
        onClick={() => setOpenInstruction(true)}
        className="flex text-primary underline cursor-pointer"
      >
        {trans.DriverInstruction.title}
      </button>
      {/* DriverInstruction */}
      {openInstruction && (
        <div
          onClick={() => setOpenInstruction(false)}
          className="fixed inset-0 bg-black/10 bg-opacity-50 flex items-center justify-center z-50"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white p-3 rounded-md w-full max-w-3xl lg:mx-40 md:px-15 px-2 relative shadow-lg max-h-[100vh] overflow-y-auto no-scrollbar flex items-center flex-col text-black text-start"
          >
            <div className="relative lg:w-[400px] w-full  h-[200px]  ">
              <Image
                src="/images/logo-about.png"
                alt="landing_image"
                width={400}
                height={200}
                className="object-contain "
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
              />
            </div>
            <div className="flex items-center justify-center flex-col gap-5 text-lg">
              <h1 className="font-bold "> {trans.DriverInstruction.title}</h1>
              <h1 className="font-semibold  text-gray-500">
                {" "}
                {trans.DriverInstruction.subTitle}
              </h1>
              <div className="max-w-3xl mx-auto p-4 space-y-5 ">
                <div>
                  <Image
                    src="/images/captain/section.png"
                    alt="landing_image"
                    width={200}
                    height={150}
                    className="float-right ml-4 mb-2 object-contain"
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
                    quality={100}
                    priority
                  />
                  <p className="text-start text-gray-800">
                    {trans.DriverInstruction.desc}
                  </p>
                </div>

                <div className="space-y-5 text-start">
                  <h1 className="text-2xl font-bold text-start w-full ">
                    {trans.title}
                  </h1>
                  <p className="">{trans.desc}</p>
                </div>
                <div className="space-y-3">
                  <h1 className="font-bold flex items-center gap-3">
                    {" "}
                    <FaCircleCheck className="text-emerald-700 text-2xl" />
                    {trans.DriverInstruction.Step_by_Step.title}
                  </h1>
                  <div className="flex items-center  w-full gap-2 flex-col text-[15px]">
                    {/* step  1  */}
                    <div className="lg:px-9 px-2">
                      <h1 className="font-bold">
                        {trans.DriverInstruction.Step_by_Step.step_1.title}
                      </h1>
                      <div className="px-4 flex items-center max-md:flex-col">
                        <div>
                          <span>
                            {
                              trans.DriverInstruction.Step_by_Step.step_1.desc
                                .snap_1
                            }
                          </span>
                          <span className="text-primary underline">
                            <Link href={"https://airportandcitytransfer.com/"}>
                              {
                                trans.DriverInstruction.Step_by_Step.step_1.desc
                                  .link
                              }
                            </Link>
                          </span>
                          <span>
                            {
                              trans.DriverInstruction.Step_by_Step.step_1.desc
                                .snap_2
                            }
                          </span>
                        </div>
                        <div className="relative  w-2/3   h-[100px] ">
                          <Image
                            src="/images/captain/complete.png"
                            alt="image"
                            fill
                            className=""
                          />
                        </div>
                      </div>
                    </div>
                    {/* stpe 2  */}
                    <div className="lg:px-9 px-2 ">
                      <h1 className="font-bold">
                        {trans.DriverInstruction.Step_by_Step.step_2.title}
                      </h1>
                      <div className="px-4 flex items-center justify-between w-full max-md:flex-col gap-4 ">
                        <span>
                          {" "}
                          {trans.DriverInstruction.Step_by_Step.step_2.desc}
                        </span>

                        <div className="relative w-full h-[150px] ">
                          <Image
                            src="/images/captain/step_2.png"
                            alt="image"
                            className=""
                            fill
                          />
                        </div>
                      </div>
                    </div>
                    {/* step 3  */}
                    <div className="lg:px-9 px-2 w-full">
                      <h1 className="font-bold">
                        {trans.DriverInstruction.Step_by_Step.step_3.title}
                      </h1>
                      <div className="px-4 flex items-center justify-between w-full max-md:flex-col  gap-4 ">
                        <div>
                          {trans.DriverInstruction.Step_by_Step.step_3.dsec.sub}
                          <ul className="list-disc md:ps-15 ps-2">
                            {trans.DriverInstruction.Step_by_Step.step_3.dsec.list.map(
                              (ite: string, index: number) => (
                                <li key={index}>{ite}</li>
                              )
                            )}
                          </ul>
                        </div>

                        <div className=" relative md:w-[230px] w-full h-[150px] ">
                          <Image
                            src="/images/captain/step_3.png"
                            alt="image"
                            className=""
                            fill
                          />
                        </div>
                      </div>
                    </div>
                    {/* step 4  */}
                    <div className="lg:px-9 px-2 w-full">
                      <h1 className="font-bold">
                        {trans.DriverInstruction.Step_by_Step.step_4.title}
                      </h1>
                    </div>
                    {/* step 5  */}
                    <div className="lg:px-9 px-2 w-full">
                      <h1 className="font-bold">
                        {trans.DriverInstruction.Step_by_Step.step_5.title}
                      </h1>
                      <div className="px-4 flex items-center justify-between w-full max-md:flex-col gap-4 ">
                        <div>
                          {trans.DriverInstruction.Step_by_Step.step_5.dsec.sub}
                          <ul className="list-disc md:ps-15 ps-2">
                            {trans.DriverInstruction.Step_by_Step.step_5.dsec.list.map(
                              (ite: string, index: number) => (
                                <li key={index}>{ite}</li>
                              )
                            )}
                          </ul>
                        </div>

                        <div className="  ">
                          <Image
                            src="/images/captain/step_4.png"
                            alt="image"
                            className=""
                            width={150}
                            height={70}
                          />
                        </div>
                      </div>
                    </div>
                    {/* step 6  */}
                    <div className="lg:px-9 px-2 w-full">
                      <h1 className="font-bold">
                        {trans.DriverInstruction.Step_by_Step.step_6.title}
                      </h1>
                      <div className="px-4 flex items-center justify-between flex-col w-full  gap-4 ">
                        <div>
                          {trans.DriverInstruction.Step_by_Step.step_6.desc}
                        </div>

                        <div className=" relative md:w-2/3 w-full h-[200px] ">
                          <Image
                            src="/images/captain/step_1.png"
                            alt="image"
                            className=""
                            fill
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="py-4 border-y-2 font-bold text-center">
                  {trans.DriverInstruction.section_proud.map(
                    (proud: string, ind: number) => (
                      <span
                        key={ind}
                        className={ind === 1 || ind === 3 ? "text-primary" : ""}
                      >
                        {proud}
                      </span>
                    )
                  )}
                </div>
                <div className="relative lg:w-[400px] w-full  md:h-[200px] h-[150px] mx-auto  ">
                  <Image
                    src="/images/logo-about.png"
                    alt="landing_image"
                    width={400}
                    height={200}
                    className="object-contain "
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
                  />
                </div>
                <Button
                  type="button"
                  className="w-full text-lg"
                  onClick={() => setOpenInstruction(false)}
                >
                  {trans.botton}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
