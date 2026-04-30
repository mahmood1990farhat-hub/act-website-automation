"use client";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import FileField from "../auth/FileField";
import { Button } from "@/components/ui/button";
import { extract_error } from "@/lib/api/errorApi";
import GlobalModal from "../GlobalModal";
import { FaTimesCircle } from "react-icons/fa";
import { Locale } from "../../../../i18n.config";
import { getCookie } from "cookies-next";
import { fetchData } from "@/lib/api/fetchData";
import { toast } from "react-toastify";
import { useRouter } from "next/navigation";
import Link from "next/link";

type FormData = {
  pco?: FileList;
  dbs?: FileList;
  dvla?: FileList;
  MOT?: FileList;
  PHV?: FileList;
};

interface ModificationStatus {
  status: string;
  files_need_modification: string[];
  files_with_labels: Array<{
    file_name: string;
    label: string;
  }>;
  modification_confirmed: boolean;
  rejection_reason?: string;
  message: string;
}

interface FileFieldConfig {
  name: keyof FormData;
  label: string;
  description: string;
}

const fileConfigs: Record<string, FileFieldConfig> = {
  pco: {
    name: "pco",
    label: "PCO Driver Licence (TfL Private Hire Driver Licence)",
    description: "Upload the front of your Transport for London (TfL) Private Hire Driver Licence showing your name, badge number, expiry date, and photo. This is mandatory for all drivers.",
  },
  dbs: {
    name: "dbs",
    label: "Enhanced DBS Certificate (Disclosure and Barring Service)",
    description: "Upload a recent Enhanced Disclosure and Barring Service (DBS) certificate issued within the last 6 months. This background check is required for passenger safety.",
  },
  dvla: {
    name: "dvla",
    label: "UK DVLA Driving Licence (Both Sides)",
    description: "Upload clear photos of both the front and back of your UK Driver and Vehicle Licensing Agency (DVLA) driving licence showing all details including your photo, address, and licence categories.",
  },
  mot: {
    name: "MOT",
    label: "MOT Certificate (Ministry of Transport Test)",
    description: "Upload your latest MOT (Ministry of Transport) certificate confirming your vehicle has passed its annual safety inspection. Vehicles less than 6 months old are exempt.",
  },
  phv: {
    name: "PHV",
    label: "PHV Licence (Private Hire Vehicle Licence)",
    description: "Upload your Transport for London (TfL) Private Hire Vehicle (PHV) licence. If you rent the vehicle, request this document from your vehicle operator.",
  },
};

export default function ModifyDocuments({
  trans,
  transInfo,
  locale,
}: {
  locale: Locale;
  trans: any;
  transInfo: any;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [errorSignMess, setErrorSignMess] = useState<string | undefined>();
  const [openModal, setOpenModal] = useState(false);
  const [modificationStatus, setModificationStatus] = useState<ModificationStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>();

  const [token, setToken] = useState<string | undefined>();

  useEffect(() => {
    setToken(getCookie("userToken") as string | undefined);
    fetchModificationStatus();
  }, []);

  const fetchModificationStatus = async () => {
    try {
      const token = getCookie("userToken") as string | undefined;
      if (!token) {
        router.push(`/${locale}/auth`);
        return;
      }

      const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${BASE_URL}/api/drivers/onboarding/documents/modification-status/`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch modification status");
      }

      const data: ModificationStatus = await response.json();
      setModificationStatus(data);
      setLoadingStatus(false);
    } catch (error) {
      console.error("Error fetching modification status:", error);
      toast.error("Failed to load modification details. Please try again.");
      setLoadingStatus(false);
    }
  };

  const onSubmit = async (data: FormData) => {
    setIsLoading(true);
    const formData = new FormData();

    // Only append files that need modification
    if (modificationStatus?.files_need_modification) {
      modificationStatus.files_need_modification.forEach((fileName) => {
        // Map API file names to form field names
        const normalizedFileName = fileName.toLowerCase();
        let formFieldName: keyof FormData;
        
        if (normalizedFileName === "mot") {
          formFieldName = "MOT";
        } else if (normalizedFileName === "phv") {
          formFieldName = "PHV";
        } else {
          formFieldName = normalizedFileName as keyof FormData;
        }
        
        const fileData = data[formFieldName];
        
        if (fileData && fileData.length > 0) {
          // Map to API field names (lowercase)
          if (normalizedFileName === "mot") {
            formData.append("mot", fileData[0]);
          } else if (normalizedFileName === "phv") {
            formData.append("phv", fileData[0]);
          } else {
            formData.append(normalizedFileName, fileData[0]);
          }
        }
      });
    }

    const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

    try {
      // Use the original step2 API endpoint
      const response = await fetch(`${BASE_URL}/api/drivers/onboarding/step2/`, {
        method: "POST",
        body: formData,
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      });

      const result = await response.json();
      
      if (!response.ok) {
        setErrorSignMess(extract_error(result));
        setIsLoading(false);
        throw result;
      }


      setIsLoading(false);
      setOpenModal(true);
    } catch (error) {
      setIsLoading(false);
      console.error("Error:", error);
    }
  };

  if (loadingStatus) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted">Loading modification details...</p>
        </div>
      </div>
    );
  }

  if (!modificationStatus || modificationStatus.files_need_modification.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-lg mb-4">No documents need modification at this time.</p>
          <Link href={`/${locale}`} className="text-primary underline">
            Go to Home
          </Link>
        </div>
      </div>
    );
  }

  const filesToModify = modificationStatus.files_need_modification.map((fileName) => {
    const normalizedFileName = fileName.toLowerCase();
    const config = fileConfigs[normalizedFileName];
    
    // Map file names to form field names
    let formFieldName: keyof FormData;
    if (normalizedFileName === "mot") {
      formFieldName = "MOT";
    } else if (normalizedFileName === "phv") {
      formFieldName = "PHV";
    } else {
      formFieldName = normalizedFileName as keyof FormData;
    }
    
    return {
      fileName,
      config: config || {
        name: formFieldName,
        label: modificationStatus.files_with_labels.find((f) => f.file_name === fileName)?.label || fileName.toUpperCase(),
        description: `Please upload a new ${fileName.toUpperCase()} document.`,
      },
    };
  });

  return (
    <>
      <GlobalModal
        isOpen={openModal}
        onClose={() => {
          setOpenModal(false);
          router.push(`/${locale}`);
          router.refresh();
        }}
      >
        <div className="flex items-center justify-center flex-col gap-4">
          <h1 className="text-lg font-bold">
            {trans?.modal?.title || "Documents Submitted Successfully"}
          </h1>
          <p className="text-center">
            {trans?.modal?.desc || "Your modified documents have been submitted. We will review them and notify you once the verification is complete."}
          </p>
          <Button
            onClick={() => {
              setOpenModal(false);
              router.push(`/${locale}`);
              router.refresh();
            }}
            className="bg-primary text-black font-bold p-2 rounded"
          >
            {trans?.modal?.btu || "Go to Driver Dashboard"}
          </Button>
        </div>
      </GlobalModal>

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

      {/* Header - matching CreateCaptainAccount style */}
      <div className="mb-4 sm:mb-8 px-2 sm:px-0">
        <div className="text-center mb-4">
          <h1 className="text-lg sm:text-xl font-semibold mb-2">
            {trans?.modifyDocuments?.title || trans?.title || "Modify Documents"}
          </h1>
          <p className="text-xs sm:text-sm text-muted">
            {modificationStatus.message || "Please upload the following documents that need modification:"}
          </p>
        </div>
      </div>

      {/* Form - matching CreateCaptainAccount style */}
      <form
        className="space-y-4 sm:space-y-6   pb-8 "
        onSubmit={handleSubmit(onSubmit)}
      >
        {/* Rejection Reason */}
        {modificationStatus.rejection_reason && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-yellow-400 mb-2">Rejection Reason:</h3>
            <p className="text-sm text-gray-300">{modificationStatus.rejection_reason}</p>
          </div>
        )}

        <div className="border border-muted md:p-5 p-3 rounded-lg mb-4">
          <h2 className="text-lg text-primary font-medium text-center mb-6">
            {trans?.modifyDocuments?.documentsTitle || trans?.DriverDocuments?.title || "Documents Requiring Modification"}
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            {filesToModify.map(({ fileName, config }) => (
              <div
                key={fileName}
                className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-4 md:gap-6 items-start"
              >
                <div className="pt-3">
                  <label className="text-sm font-medium block mb-1">
                    {config.label}
                  </label>
                  <p className="text-xs text-muted">{config.description}</p>
                </div>
                <div>
                  <FileField
                    label=""
                    placeholder={fileName}
                    name={config.name}
                    register={register}
                    requiredMsg={transInfo?.locationRequired || "Required"}
                    error={errors[config.name]}
                    value={watch(config.name)}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end mt-6">
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
              trans?.modifyDocuments?.submitButton || "Update Documents"
            )}
          </Button>
        </div>
      </form>
    </>
  );
}

