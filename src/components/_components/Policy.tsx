"use client";
import React, { useState, useEffect } from "react";
import { Button } from "../ui/button";
import { IoAlertCircle } from "react-icons/io5";
import { getInstructionFile } from "@/lib/api/fetchInstructionFile";
import { languageType } from "../../../i18n.config";
import IsLoading from "./ISloading";

export default function Policy({
  trans,
  inPaymant,
  locale = "en" as languageType,
}: {
  trans: any;
  inPaymant?: any;
  locale?: languageType;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [instructionFile, setInstructionFile] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [useFallback, setUseFallback] = useState(false);

  useEffect(() => {
    if (isOpen && !instructionFile && !useFallback) {
      setIsLoading(true);
      getInstructionFile("PRIVACY_POLICY", locale)
        .then((file) => {
          if (file) {
            setInstructionFile(file);
          } else {
            setUseFallback(true);
          }
        })
        .catch(() => {
          setUseFallback(true);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [isOpen, locale, instructionFile, useFallback]);

  const handleClose = () => {
    setIsOpen(false);
    if (!instructionFile) {
      setUseFallback(false);
    }
  };

  return (
    <div>
      <button type="button" className="cursor-pointer hover:text-gray-400" onClick={() => setIsOpen(true)}> {trans.Open_button}</button>
      {isOpen && (
        <div
          onClick={handleClose}
          className="fixed inset-0 bg-black/10 bg-opacity-50 flex items-center justify-center z-50"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white text-black p-6 md:px-15 rounded-lg md:w-5/12 overflow-auto h-screen on-scrollbar space-y-3 flex flex-col items-start"
          >
            {isLoading ? (
              <div className="w-full flex items-center justify-center py-20">
                <IsLoading />
              </div>
            ) : instructionFile && !useFallback ? (
              <>
                <h1 className="text-lg font-bold">{instructionFile.title || trans.title}</h1>
                {instructionFile.description && (
                  <p className="text-sm text-gray-600">{instructionFile.description}</p>
                )}
                <div className="w-full h-[calc(100vh-250px)]">
                  <iframe
                    src={instructionFile.file_url}
                    className="w-full h-full border rounded-lg"
                    title={instructionFile.title || "Privacy Policy"}
                  />
                </div>
                <div className="flex items-center gap-4 w-full">
                  <a
                    href={instructionFile.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm"
                  >
                    Open in new tab
                  </a>
                  <a
                    href={instructionFile.file_url}
                    download
                    className="text-primary hover:underline text-sm"
                  >
                    Download PDF
                  </a>
                </div>
                <h4 className="text-gray-500 text-xs flex items-center gap-2">
                  <IoAlertCircle className="text-[#ED1F4F] text-3xl" />
                  {trans.warning}
                </h4>
                <Button type="button" onClick={handleClose} className="w-full text-lg">
                  {trans.button}
                </Button>
              </>
            ) : (
              <>
                <h1 className="text-lg font-bold">{trans.title}</h1>
                <p className="">{trans.desc}</p>
                <ol className="list-decimal space-y-3 text-[14px]">
                  {trans.elements?.map((item: any) => (
                    <div key={item.title} className="flex items-start flex-col">
                      <li className="font-bold">{item.title}</li>
                      <div>
                        {item.desc}
                        <ul className="list-disc px-8 text-sm">
                          {item.subDesc &&
                            item.subDesc.map((sub: string, indx: number) => (
                              <li className="" key={indx}>
                                {sub}
                              </li>
                            ))}
                        </ul>
                        {item.descEnd}
                      </div>
                    </div>
                  ))}
                </ol>
                <h4 className="text-gray-500 text-xs flex items-center gap-2">
                  <IoAlertCircle className="text-[#ED1F4F] text-3xl" />
                  {trans.warning}
                </h4>
                <Button type="button" onClick={handleClose} className="w-full text-lg">
                  {trans.button}
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
