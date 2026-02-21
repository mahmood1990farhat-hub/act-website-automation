import { languageType, Locale } from "../../../i18n.config";
import { Languages } from "../../constants/enums";

type InstructionFile = {
  id: number;
  file_type: string;
  file_type_display: string;
  title: string;
  file_url: string;
  description: string;
  version: number;
  updated_at: string;
};

type InstructionFilesResponse = {
  success: boolean;
  data: {
    instruction_files: InstructionFile[];
  };
};

/**
 * Fetches instruction files from the API by file type
 * @param fileType - The file type enum (TERMS_AND_CONDITIONS, FAQ, PRIVACY_POLICY, DRIVER_GUIDELINES, PASSENGER_GUIDELINES, OTHER)
 * @param locale - The locale for the request
 * @returns Promise with the instruction files response
 */
export async function fetchInstructionFile(
  fileType: string,
  locale: languageType = "en" as languageType
): Promise<InstructionFilesResponse | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const url = new URL(`${baseUrl}/api/instruction-files/`);
    url.searchParams.append("file_type", fileType);
    url.searchParams.append("locale", locale);

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store", // Always fetch fresh data
    });

    if (!response.ok) {
      console.error(`Failed to fetch instruction file: ${response.statusText}`);
      return null;
    }

    const data: InstructionFilesResponse = await response.json();
    return data;
  } catch (error) {
    console.error(`Error fetching instruction file (${fileType}):`, error);
    return null;
  }
}

/**
 * Gets the most recent active instruction file for a given type
 * @param fileType - The file type enum
 * @param locale - The locale for the request
 * @returns The most recent instruction file or null
 */
export async function getInstructionFile(
  fileType: string,
  locale: languageType = "en" as languageType
): Promise<InstructionFile | null> {
  const response = await fetchInstructionFile(fileType, locale);
  
  if (!response?.success || !response.data?.instruction_files?.length) {
    return null;
  }

  // Get the most recent file (sorted by updated_at)
  const files = response.data.instruction_files;
  const sortedFiles = files.sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  return sortedFiles[0] || null;
}
